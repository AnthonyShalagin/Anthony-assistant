// Definitions, canonical reference ranges, and "lower-is-better" hints
// for biomarkers. Definitions are 1-sentence plain language. Canonical
// ranges are used to compute status uniformly across panels (so the UI
// doesn't flip between labs that use slightly different cutoffs).

export type BiomarkerDef = {
  /** Short plain-language definition. */
  description: string;
  /** Canonical lower bound (Function-Health-style "optimal" leaning). */
  ref_low?: number;
  /** Canonical upper bound. */
  ref_high?: number;
  /** True if a lower value is better (LDL, ApoB, etc.). */
  lowerIsBetter?: boolean;
  /** Pretty-print marker name (overrides DB name if set). */
  display?: string;
};

export const BIOMARKERS: Record<string, BiomarkerDef> = {
  // ---------- Heart / Lipids ----------
  "Total Cholesterol": {
    description: "Total cholesterol in your blood — a sum of LDL, HDL, and other lipid particles.",
    ref_high: 200, lowerIsBetter: true,
  },
  "LDL-C": {
    description: "Low-density lipoprotein cholesterol — the main driver of plaque buildup in arteries.",
    ref_high: 100, lowerIsBetter: true, display: "LDL Cholesterol",
  },
  "LDL Direct": {
    description: "LDL measured directly, used when triglycerides distort calculated LDL.",
    ref_high: 100, lowerIsBetter: true,
  },
  "HDL-C": {
    description: "HDL removes excess cholesterol from the blood, reducing heart-disease and stroke risk.",
    ref_low: 40, display: "HDL Cholesterol",
  },
  Triglycerides: {
    description: "Fats in the blood — high levels are linked to insulin resistance and heart-disease risk.",
    ref_high: 150, lowerIsBetter: true,
  },
  ApoB: {
    description: "Counts every atherogenic particle (LDL, VLDL, IDL, Lp(a)). Many lipidologists consider it the single best lipid risk marker.",
    ref_high: 90, lowerIsBetter: true, display: "Apolipoprotein B",
  },
  "Non-HDL Cholesterol": {
    description: "All atherogenic cholesterol (total minus HDL). Often a better predictor than LDL alone.",
    ref_high: 130, lowerIsBetter: true,
  },
  "Chol/HDL Ratio": {
    description: "Total cholesterol divided by HDL — a quick snapshot of cardiovascular risk.",
    ref_high: 5.0, lowerIsBetter: true,
  },
  "LDL Particle Number": {
    description: "How many LDL particles are circulating. More particles = more chances to lodge in artery walls.",
    ref_high: 1138, lowerIsBetter: true,
  },
  "LDL Small": {
    description: "Small, dense LDL particles — the most atherogenic LDL subtype.",
    ref_high: 142, lowerIsBetter: true,
  },
  "LDL Medium": {
    description: "Medium-sized LDL particles. Counts here track with overall LDL particle number.",
    ref_high: 215, lowerIsBetter: true,
  },
  "HDL Large": {
    description: "Large, mature HDL particles — the most cardioprotective HDL subtype.",
    ref_low: 6729,
  },
  "LDL Peak Size": {
    description: "Average size of your LDL particles. Larger ('Pattern A') is healthier than small ('Pattern B').",
    ref_low: 222.9,
  },
  VLDL: {
    description: "Very-low-density lipoprotein cholesterol — carries triglycerides through the bloodstream.",
    ref_low: 7, ref_high: 32, lowerIsBetter: true,
  },
  "Lipoprotein (a)": {
    description: "Genetically inherited lipid particle — high values raise heart-disease and stroke risk independently of LDL.",
    ref_high: 75, lowerIsBetter: true,
  },
  "Cardio CRP": {
    description: "High-sensitivity CRP (older naming). Marker of vascular inflammation tied to cardiovascular risk.",
    ref_high: 1.0, lowerIsBetter: true,
  },
  "Omega-3 Total": {
    description: "Total omega-3 fatty acids as percent by weight. Higher is associated with lower cardiovascular and cognitive-decline risk.",
    ref_low: 5.5,
  },
  "Omega-6 Total": {
    description: "Total omega-6 fatty acids as percent by weight.",
  },
  "Omega-6/Omega-3 Ratio": {
    description: "Ratio of omega-6 to omega-3. Lower ratios (closer to 4:1) are linked to less inflammation.",
    ref_high: 4.0, lowerIsBetter: true,
  },

  // ---------- Metabolic ----------
  Glucose: {
    description: "Blood sugar after fasting. Persistently high values precede prediabetes and type 2 diabetes.",
    ref_low: 70, ref_high: 99, lowerIsBetter: true,
  },
  HbA1c: {
    description: "Three-month average of blood sugar. The gold-standard screen for diabetes risk.",
    ref_high: 5.6, lowerIsBetter: true, display: "Hemoglobin A1c",
  },
  "Insulin (fasting)": {
    description: "Fasting insulin — high values signal insulin resistance years before glucose rises.",
    ref_high: 8, lowerIsBetter: true,
  },
  eAG: {
    description: "Estimated Average Glucose, derived from your A1c.",
    ref_high: 114, lowerIsBetter: true,
  },
  "Uric Acid": {
    description: "Byproduct of purine breakdown. High levels can crystalize in joints (gout) and may stress the kidneys.",
    ref_low: 4.0, ref_high: 8.0, lowerIsBetter: true,
  },

  // ---------- Hormones / Thyroid ----------
  TSH: {
    description: "Thyroid Stimulating Hormone — the brain's signal to the thyroid. Out-of-range values flag hypo- or hyperthyroidism.",
    ref_low: 0.4, ref_high: 4.5,
  },
  "Free T4": {
    description: "Unbound thyroxine — the active reserve of thyroid hormone available to your tissues.",
    ref_low: 0.9, ref_high: 1.7,
  },
  "Free T3": {
    description: "Unbound triiodothyronine — the active form of thyroid hormone working in your tissues.",
    ref_low: 2.3, ref_high: 4.2,
  },
  "Free T4 Index (T7)": {
    description: "Older calculation of free thyroid hormone, now usually replaced by direct Free T4.",
    ref_low: 1.4, ref_high: 3.8,
  },
  "Cortisol (Total)": {
    description: "Stress hormone. Best interpreted alongside time of day — peaks in the morning, drops by evening.",
    ref_low: 4, ref_high: 22,
  },

  // ---------- Inflammation ----------
  "hs-CRP": {
    description: "High-sensitivity C-reactive protein — measures low-grade systemic inflammation linked to heart disease.",
    ref_high: 1.0, lowerIsBetter: true,
  },
  "ESR (Westergren)": {
    description: "Erythrocyte sedimentation rate — a non-specific inflammation marker, often elevated in autoimmune flares.",
    ref_high: 15, lowerIsBetter: true,
  },

  // ---------- Nutrients ----------
  "Vitamin D, 25-OH": {
    description: "The storage form of vitamin D. Affects bone health, immune function, mood, and athletic performance.",
    ref_low: 30, ref_high: 100,
  },
  "Vitamin B12": {
    description: "Critical for nerve function and red-blood-cell production. Vegans, older adults, and PPI users are at risk for deficiency.",
    ref_low: 232, ref_high: 1245,
  },
  "Folate (serum)": {
    description: "B-vitamin essential for DNA synthesis and homocysteine metabolism.",
    ref_low: 5.4,
  },
  Ferritin: {
    description: "Stored iron. Low values indicate depleted reserves before anemia shows up; very high can flag inflammation.",
    ref_low: 30, ref_high: 400,
  },
  "Iron, Total": {
    description: "Iron currently bound to transferrin in circulation. Best read alongside TIBC and ferritin.",
    ref_low: 50, ref_high: 195,
  },
  TIBC: {
    description: "Total iron-binding capacity — how much transferrin is available to carry iron.",
    ref_low: 250, ref_high: 425,
  },
  UIBC: {
    description: "Unsaturated iron-binding capacity — transferrin sites not yet bound to iron.",
    ref_low: 110, ref_high: 370,
  },
  "Magnesium, RBC": {
    description: "Magnesium inside red blood cells — a more sensitive measure of body magnesium status than serum.",
    ref_low: 4.0, ref_high: 6.4,
  },
  Iodine: {
    description: "Essential for thyroid hormone production. Low intake is common in people who avoid iodized salt or sea vegetables.",
    ref_low: 52, ref_high: 109,
  },
  Selenium: {
    description: "Antioxidant trace mineral involved in thyroid hormone activation and immune function.",
    ref_low: 63, ref_high: 160,
  },
  "Copper, Blood": {
    description: "Essential trace mineral. Both deficiency and excess can cause neurological and metabolic issues.",
    ref_low: 70, ref_high: 175,
  },

  // ---------- Toxins ----------
  "Mercury, Blood": {
    description: "Recent exposure to mercury, mostly from fish (especially tuna, swordfish, mackerel). Elevated levels can affect the nervous system.",
    ref_high: 10, lowerIsBetter: true,
  },
  "Arsenic, Blood": {
    description: "Exposure to arsenic — sources include some seafood, rice, and contaminated water.",
    ref_high: 23, lowerIsBetter: true,
  },
  "Aluminum, Blood": {
    description: "Aluminum levels in blood. Most adults have very low levels unless occupationally exposed.",
    ref_high: 20, lowerIsBetter: true,
  },

  // ---------- Liver ----------
  AST: {
    description: "Liver enzyme also released by skeletal muscle. Acute spikes can follow heavy training.",
    ref_low: 10, ref_high: 40, lowerIsBetter: true,
  },
  ALT: {
    description: "The most liver-specific enzyme. Sustained elevations suggest hepatic stress (fatty liver, alcohol, meds).",
    ref_low: 9, ref_high: 46, lowerIsBetter: true,
  },
  "Alkaline Phosphatase": {
    description: "Enzyme from liver, bile ducts, and bone. Out-of-range values can flag liver, gallbladder, or bone activity.",
    ref_low: 36, ref_high: 130,
  },
  "Bilirubin, Total": {
    description: "Breakdown product of red blood cells. Mildly elevated values are often Gilbert's syndrome (benign).",
    ref_low: 0.2, ref_high: 1.2,
  },
  "Total Protein": {
    description: "Sum of albumin and globulins in serum — a broad indicator of liver, kidney, and immune status.",
    ref_low: 6.1, ref_high: 8.1,
  },
  Albumin: {
    description: "The most abundant blood protein. Low values can indicate malnutrition, inflammation, or liver/kidney issues.",
    ref_low: 3.6, ref_high: 5.1,
  },
  Globulin: {
    description: "Family of blood proteins that includes antibodies. Elevations can signal chronic inflammation or infection.",
    ref_low: 1.9, ref_high: 3.7,
  },

  // ---------- Kidney ----------
  BUN: {
    description: "Blood urea nitrogen — a kidney filtration marker also affected by hydration and protein intake.",
    ref_low: 7, ref_high: 25,
  },
  Creatinine: {
    description: "Muscle-breakdown byproduct cleared by the kidneys. Used to estimate eGFR.",
    ref_low: 0.6, ref_high: 1.3,
  },
  eGFR: {
    description: "Estimated glomerular filtration rate — how well your kidneys filter blood. Higher is better.",
    ref_low: 60,
  },
  "BUN/Creatinine Ratio": {
    description: "Ratio used to distinguish dehydration from kidney problems.",
    ref_low: 10, ref_high: 28,
  },

  // ---------- Electrolytes ----------
  Sodium: { description: "Primary extracellular electrolyte, tightly regulated by the kidneys.", ref_low: 135, ref_high: 146 },
  Potassium: { description: "Critical intracellular electrolyte for nerve and muscle function.", ref_low: 3.5, ref_high: 5.3 },
  Chloride: { description: "Pairs with sodium to maintain blood pH and fluid balance.", ref_low: 98, ref_high: 110 },
  Calcium: { description: "Total serum calcium, regulated by parathyroid hormone and vitamin D.", ref_low: 8.6, ref_high: 10.3 },
  "Carbon Dioxide": { description: "Bicarbonate — a buffer for blood pH balance.", ref_low: 20, ref_high: 32 },

  // ---------- CBC ----------
  WBC: { description: "White blood cell count — your immune system's fighter pool.", ref_low: 3.8, ref_high: 10.8 },
  RBC: { description: "Red blood cell count — oxygen-carrying cells.", ref_low: 4.2, ref_high: 5.8 },
  Hemoglobin: { description: "Oxygen-carrying protein inside red blood cells.", ref_low: 13.2, ref_high: 17.1 },
  Hematocrit: { description: "Percent of blood volume made up of red blood cells.", ref_low: 38.5, ref_high: 50.0 },
  MCV: { description: "Mean corpuscular volume — average size of a red blood cell.", ref_low: 80, ref_high: 100 },
  MCH: { description: "Mean corpuscular hemoglobin — average hemoglobin content per red blood cell.", ref_low: 27, ref_high: 33 },
  MCHC: { description: "Mean corpuscular hemoglobin concentration — hemoglobin density inside red blood cells.", ref_low: 32, ref_high: 36 },
  RDW: { description: "Red cell distribution width — variation in red-blood-cell size. High values can flag anemia or B12/iron deficiency.", ref_low: 11, ref_high: 15 },
  Platelets: { description: "Cells that clot blood and seal vessel injuries.", ref_low: 140, ref_high: 400 },
  MPV: { description: "Mean platelet volume — average platelet size.", ref_low: 7.5, ref_high: 12.5 },
  "Neutrophils %": {
    description: "Percent of white blood cells that are neutrophils — the body's first responders to bacterial infection.",
    ref_low: 38, ref_high: 80,
  },
  "Lymphocytes %": {
    description: "Percent of white blood cells that are lymphocytes — drive antiviral and adaptive immunity.",
    ref_low: 15, ref_high: 49,
  },
  "Monocytes %": {
    description: "Percent of white blood cells that are monocytes — clean up tissue debris and chronic invaders.",
    ref_low: 0, ref_high: 13,
  },
  "Eosinophils %": {
    description: "White blood cells that respond to allergens and parasites. Elevated levels often track allergies.",
    ref_low: 0, ref_high: 8,
  },
  "Basophils %": {
    description: "Rare white blood cells involved in allergic and inflammatory responses.",
    ref_low: 0, ref_high: 2,
  },
  "Eosinophils, Absolute": {
    description: "Absolute eosinophil count. Persistently high values warrant a deeper look at allergies or other triggers.",
    ref_low: 15, ref_high: 500,
  },
  "Monocytes, Absolute": {
    description: "Absolute monocyte count. Mild elevations can follow viral infections or chronic inflammation.",
    ref_low: 200, ref_high: 950,
  },

  // ---------- Other ----------
  "EBV-VCA, IgG": {
    description: "Antibodies indicating past Epstein-Barr virus infection (mono). Elevated values are common and usually not actionable.",
  },
};

export function getDef(marker: string): BiomarkerDef | undefined {
  return BIOMARKERS[marker];
}

/** Compute status from a value using canonical ranges. */
export function canonicalStatus(
  marker: string,
  value: number
): "optimal" | "high" | "low" | "normal" {
  const def = BIOMARKERS[marker];
  if (!def) return "normal";
  if (def.ref_low != null && value < def.ref_low) return "low";
  if (def.ref_high != null && value > def.ref_high) return "high";
  return "optimal";
}
