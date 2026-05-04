// Definitions and "lower-is-better" hints for biomarkers.
// One-sentence definitions in plain language, mirroring Function Health's tone.

export type BiomarkerDef = {
  /** Short plain-language definition. */
  description: string;
  /** True if a lower value is better (LDL, ApoB, etc.). */
  lowerIsBetter?: boolean;
  /** Pretty-print marker name (overrides DB name if set). */
  display?: string;
};

export const BIOMARKERS: Record<string, BiomarkerDef> = {
  // ---------- Heart ----------
  "Total Cholesterol": {
    description: "Total cholesterol in your blood — a sum of LDL, HDL, and other lipid particles.",
    lowerIsBetter: true,
  },
  "LDL-C": {
    description: "Low-density lipoprotein cholesterol — the main driver of plaque buildup in arteries.",
    lowerIsBetter: true,
    display: "LDL Cholesterol",
  },
  "LDL Direct": {
    description: "LDL measured directly, used when triglycerides distort calculated LDL.",
    lowerIsBetter: true,
  },
  "HDL-C": {
    description: "HDL removes excess cholesterol from the blood, reducing heart-disease and stroke risk.",
    display: "HDL Cholesterol",
  },
  Triglycerides: {
    description: "Fats in the blood — high levels are linked to insulin resistance and heart-disease risk.",
    lowerIsBetter: true,
  },
  ApoB: {
    description: "Counts every atherogenic particle (LDL, VLDL, IDL, Lp(a)). Many lipidologists consider it the single best lipid risk marker.",
    lowerIsBetter: true,
    display: "Apolipoprotein B",
  },
  "Non-HDL Cholesterol": {
    description: "All atherogenic cholesterol (total minus HDL). Often a better predictor than LDL alone.",
    lowerIsBetter: true,
  },
  "Chol/HDL Ratio": {
    description: "Total cholesterol divided by HDL — a quick snapshot of cardiovascular risk.",
    lowerIsBetter: true,
  },
  "LDL Particle Number": {
    description: "How many LDL particles are circulating. More particles = more chances to lodge in artery walls.",
    lowerIsBetter: true,
  },
  "LDL Small": {
    description: "Small, dense LDL particles — the most atherogenic LDL subtype.",
    lowerIsBetter: true,
  },
  "LDL Medium": {
    description: "Medium-sized LDL particles. Counts here track with overall LDL particle number.",
    lowerIsBetter: true,
  },
  "HDL Large": {
    description: "Large, mature HDL particles — the most cardioprotective HDL subtype.",
  },
  "LDL Peak Size": {
    description: "Average size of your LDL particles. Larger ('Pattern A') is healthier than small ('Pattern B').",
  },
  VLDL: {
    description: "Very-low-density lipoprotein cholesterol — carries triglycerides through the bloodstream.",
    lowerIsBetter: true,
  },
  "Cardio CRP": {
    description: "High-sensitivity CRP (older naming). Marker of vascular inflammation tied to cardiovascular risk.",
    lowerIsBetter: true,
  },

  // ---------- Metabolic ----------
  Glucose: {
    description: "Blood sugar after fasting. Persistently high values precede prediabetes and type 2 diabetes.",
    lowerIsBetter: true,
  },
  HbA1c: {
    description: "Three-month average of blood sugar. The gold-standard screen for diabetes risk.",
    lowerIsBetter: true,
    display: "Hemoglobin A1c",
  },
  "Insulin (fasting)": {
    description: "Fasting insulin — high values signal insulin resistance years before glucose rises.",
    lowerIsBetter: true,
  },
  eAG: {
    description: "Estimated Average Glucose, derived from your A1c.",
    lowerIsBetter: true,
  },
  "Uric Acid": {
    description: "Byproduct of purine breakdown. High levels can crystalize in joints (gout) and may stress the kidneys.",
    lowerIsBetter: true,
  },

  // ---------- Hormones ----------
  TSH: {
    description: "Thyroid Stimulating Hormone — the brain's signal to the thyroid. Out-of-range values flag hypo- or hyperthyroidism.",
  },
  "Free T4": {
    description: "Unbound thyroxine — the active reserve of thyroid hormone available to your tissues.",
  },
  "Free T4 Index (T7)": {
    description: "Older calculation of free thyroid hormone, now usually replaced by direct Free T4.",
  },
  "Cortisol (Total)": {
    description: "Stress hormone. Best interpreted alongside time of day — peaks in the morning, drops by evening.",
  },

  // ---------- Inflammation ----------
  "hs-CRP": {
    description: "High-sensitivity C-reactive protein — measures low-grade systemic inflammation linked to heart disease.",
    lowerIsBetter: true,
  },
  "ESR (Westergren)": {
    description: "Erythrocyte sedimentation rate — a non-specific inflammation marker, often elevated in autoimmune flares.",
    lowerIsBetter: true,
  },

  // ---------- Nutrients ----------
  "Vitamin D, 25-OH": {
    description: "The storage form of vitamin D. Affects bone health, immune function, mood, and athletic performance.",
  },
  "Vitamin B12": {
    description: "Critical for nerve function and red-blood-cell production. Vegans, older adults, and PPI users are at risk for deficiency.",
  },
  "Folate (serum)": {
    description: "B-vitamin essential for DNA synthesis and homocysteine metabolism.",
  },
  Ferritin: {
    description: "Stored iron. Low values indicate depleted reserves before anemia shows up; very high can flag inflammation.",
  },
  "Iron, Total": {
    description: "Iron currently bound to transferrin in circulation. Best read alongside TIBC and ferritin.",
  },
  TIBC: {
    description: "Total iron-binding capacity — how much transferrin is available to carry iron.",
  },
  UIBC: {
    description: "Unsaturated iron-binding capacity — transferrin sites not yet bound to iron.",
  },
  "Magnesium, RBC": {
    description: "Magnesium inside red blood cells — a more sensitive measure of body magnesium status than serum.",
  },

  // ---------- Toxins ----------
  "Mercury, Blood": {
    description: "Recent exposure to mercury, mostly from fish (especially tuna, swordfish, mackerel). Elevated levels can affect the nervous system.",
    lowerIsBetter: true,
  },

  // ---------- Liver ----------
  AST: {
    description: "Liver enzyme also released by skeletal muscle. Acute spikes can follow heavy training.",
    lowerIsBetter: true,
  },
  ALT: {
    description: "The most liver-specific enzyme. Sustained elevations suggest hepatic stress (fatty liver, alcohol, meds).",
    lowerIsBetter: true,
  },
  "Alkaline Phosphatase": {
    description: "Enzyme from liver, bile ducts, and bone. Out-of-range values can flag liver, gallbladder, or bone activity.",
  },
  "Bilirubin, Total": {
    description: "Breakdown product of red blood cells. Mildly elevated values are often Gilbert's syndrome (benign).",
  },
  "Total Protein": {
    description: "Sum of albumin and globulins in serum — a broad indicator of liver, kidney, and immune status.",
  },
  Albumin: {
    description: "The most abundant blood protein. Low values can indicate malnutrition, inflammation, or liver/kidney issues.",
  },

  // ---------- Kidney ----------
  BUN: {
    description: "Blood urea nitrogen — a kidney filtration marker also affected by hydration and protein intake.",
  },
  Creatinine: {
    description: "Muscle-breakdown byproduct cleared by the kidneys. Used to estimate eGFR.",
  },

  // ---------- Electrolytes ----------
  Sodium: { description: "Primary extracellular electrolyte, tightly regulated by the kidneys." },
  Potassium: { description: "Critical intracellular electrolyte for nerve and muscle function." },
  Chloride: { description: "Pairs with sodium to maintain blood pH and fluid balance." },
  Calcium: { description: "Total serum calcium, regulated by parathyroid hormone and vitamin D." },
  "Carbon Dioxide": { description: "Bicarbonate — a buffer for blood pH balance." },

  // ---------- CBC ----------
  WBC: { description: "White blood cell count — your immune system's fighter pool." },
  RBC: { description: "Red blood cell count — oxygen-carrying cells." },
  Hemoglobin: { description: "Oxygen-carrying protein inside red blood cells." },
  Hematocrit: { description: "Percent of blood volume made up of red blood cells." },
  Platelets: { description: "Cells that clot blood and seal vessel injuries." },
  "Eosinophils %": {
    description: "White blood cells that respond to allergens and parasites. Elevated levels often track allergies.",
  },
  "Eosinophils, Absolute": {
    description: "Absolute eosinophil count. Persistently high values warrant a deeper look at allergies or other triggers.",
  },
  "Monocytes, Absolute": {
    description: "Absolute monocyte count. Mild elevations can follow viral infections or chronic inflammation.",
  },
  "Neutrophils %": {
    description: "Percent of white blood cells that are neutrophils — the body's first responders to bacterial infection.",
  },

  // ---------- Other ----------
  "EBV-VCA, IgG": {
    description: "Antibodies indicating past Epstein-Barr virus infection (mono). Elevated values are common and usually not actionable.",
  },
};

export function getDef(marker: string): BiomarkerDef | undefined {
  return BIOMARKERS[marker];
}
