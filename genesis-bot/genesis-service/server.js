const http = require("http");
const BlueLinky = require("bluelinky");

// Load .env manually (no extra dependencies)
const fs = require("fs");
const path = require("path");
const envPath = path.join(__dirname, ".env");
if (fs.existsSync(envPath)) {
  fs.readFileSync(envPath, "utf8")
    .split("\n")
    .filter((line) => line && !line.startsWith("#"))
    .forEach((line) => {
      const [key, ...vals] = line.split("=");
      if (key && vals.length) {
        process.env[key.trim()] = vals.join("=").trim();
      }
    });
}

const PORT = parseInt(process.env.PORT || "3100", 10);

const VALID_COMMANDS = [
  "start", "start-winter", "start-summer", "start-preset",
  "stop", "lock", "unlock", "status",
];

let client = null;
let vehicle = null;
let connecting = false;

async function connect() {
  if (vehicle) return vehicle;
  if (connecting) {
    // Wait for existing connection attempt
    for (let i = 0; i < 60; i++) {
      await new Promise((r) => setTimeout(r, 500));
      if (vehicle) return vehicle;
    }
    throw new Error("Connection timeout (waiting for existing attempt)");
  }

  connecting = true;
  console.log("[Genesis] Connecting...");

  try {
    client = new BlueLinky({
      username: process.env.GENESIS_USERNAME,
      password: process.env.GENESIS_PASSWORD,
      brand: "genesis",
      region: "US",
      pin: process.env.GENESIS_PIN,
    });

    await new Promise((resolve, reject) => {
      client.on("ready", resolve);
      client.on("error", reject);
      setTimeout(() => reject(new Error("Connection timeout (30s)")), 30000);
    });

    console.log("[Genesis] Connected");

    const vehicles = await client.getVehicles();
    if (vehicles.length === 0) {
      throw new Error("No vehicles found");
    }

    const vin = process.env.GENESIS_VIN;
    if (vin) {
      vehicle = vehicles.find(
        (v) => v.vehicleConfig.vin.toUpperCase() === vin.toUpperCase()
      );
      if (!vehicle) throw new Error(`VIN ${vin} not found`);
    } else {
      vehicle = vehicles[0];
    }

    console.log("[Genesis] Vehicle:", vehicle.vehicleConfig.vin);
    return vehicle;
  } catch (err) {
    client = null;
    vehicle = null;
    throw err;
  } finally {
    connecting = false;
  }
}

async function executeCommand(command) {
  const v = await connect();

  switch (command) {
    case "start":
      await v.start({
        hvac: true, duration: 10, temperature: 72,
        defrost: false, heatedFeatures: false, unit: "F",
      });
      return { success: true, message: "GV70 started (72°F)" };

    case "start-winter":
      await v.start({
        hvac: true, duration: 10, temperature: 80,
        defrost: true, heatedFeatures: true, unit: "F",
      });
      return { success: true, message: "GV70 started — winter (80°F, heated seats, defrost)" };

    case "start-summer":
      await v.start({
        hvac: true, duration: 10, temperature: 65,
        defrost: false, heatedFeatures: false, unit: "F",
        seatClimateSettings: { driverSeat: 8, passengerSeat: 8 },
      });
      return { success: true, message: "GV70 started — summer (65°F, cooled seats)" };

    case "start-preset":
      await v.start({ hvac: true, duration: 10 });
      return { success: true, message: "GV70 started — preset climate" };

    case "stop":
      await v.stop();
      return { success: true, message: "GV70 engine stopped" };

    case "lock":
      await v.lock();
      return { success: true, message: "GV70 doors locked" };

    case "unlock":
      await v.unlock();
      return { success: true, message: "GV70 doors unlocked" };

    case "status":
      const status = await v.status({ refresh: false, parsed: true });
      if (!status) return { success: false, message: "Could not get status" };
      const locked = status.chassis?.locked ? "Locked" : "Unlocked";
      const engineOn = status.engine?.ignition ? "Running" : "Off";
      return { success: true, message: `GV70: Engine ${engineOn}, Doors ${locked}` };

    default:
      return { success: false, message: `Unknown command: ${command}` };
  }
}

// HTTP server — only accepts requests from localhost
const server = http.createServer(async (req, res) => {
  // Only allow POST /command
  if (req.method !== "POST" || req.url !== "/command") {
    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "Not found" }));
    return;
  }

  // Read body
  let body = "";
  for await (const chunk of req) body += chunk;

  let parsed;
  try {
    parsed = JSON.parse(body);
  } catch {
    res.writeHead(400, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "Invalid JSON" }));
    return;
  }

  const command = parsed.command?.toLowerCase();
  if (!command || !VALID_COMMANDS.includes(command)) {
    res.writeHead(400, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: `Invalid command. Use: ${VALID_COMMANDS.join(", ")}` }));
    return;
  }

  console.log(`[API] Executing: ${command}`);
  try {
    const result = await executeCommand(command);
    console.log(`[API] Result: ${result.message}`);
    const status = result.success ? 200 : 502;
    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(JSON.stringify(result));
  } catch (err) {
    console.error(`[API] Error:`, err.message);
    // Reset connection on auth errors
    if (err.message.includes("auth") || err.message.includes("login") || err.message.includes("token")) {
      client = null;
      vehicle = null;
    }
    res.writeHead(500, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ success: false, message: err.message }));
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[Genesis Service] Running on http://127.0.0.1:${PORT}`);
  // Pre-connect on startup
  connect().catch((err) => console.error("[Genesis] Initial connection failed:", err.message));
});
