"""Syllabus MCQs for the papers students are sitting now.

Each item is one stem, four options of the same kind, and one answer.
High-mark topics are lab work, plus-two science, automobile systems,
and VFA agriculture / survey.
"""

def _item(topic, text, choices, answer, explanation):
    letters = ("A", "B", "C", "D")
    return {
        "topic": topic,
        "text": text,
        "options": {letters[i]: choices[i] for i in range(4)},
        "correct_answer": answer,
        "explanation": explanation,
    }


LAB = "Lab Safety and Instruments"
PHY = "Physics"
CHEM = "Chemistry"
BIO = "Biology and Public Health"
AGRI = "Vocational Agriculture Topics"
ENGINE = "Engine and Fuel System"
BRAKE = "Brake Clutch and Transmission"
STEER = "Steering and Suspension"
COOL = "Cooling and Lubrication"
ELEC = "Auto Electrical"

SYLLABUS_MCQS = [
    _item(LAB, "Which instrument is used to observe cells and microorganisms in a teaching laboratory?", ["Compound microscope", "Centrifuge", "Autoclave", "Incubator"], "A", "A compound microscope magnifies cells. A centrifuge separates mixtures, an autoclave sterilizes, and an incubator keeps cultures warm."),
    _item(LAB, "A laboratory autoclave is normally operated at which condition?", ["121°C and 15 psi", "37°C and 1 psi", "100°C and 5 psi", "60°C and 30 psi"], "A", "Moist heat sterilization in an autoclave is commonly done at 121°C and 15 psi for about 15 minutes."),
    _item(LAB, "What does a centrifuge do to a liquid sample?", ["Separates components by density", "Measures the pH", "Sterilizes the sample", "Counts the cells directly"], "A", "Spinning throws denser particles outward, so components separate by density."),
    _item(LAB, "Which glassware is meant for transferring a measured volume of liquid?", ["Pipette", "Beaker", "Test tube", "Watch glass"], "A", "A pipette delivers a known volume. A beaker is only for holding or rough transfer."),
    _item(LAB, "Blue litmus paper turns which colour in an acidic solution?", ["Red", "Blue", "Green", "Colourless"], "A", "Acid turns blue litmus red. Base turns red litmus blue."),
    _item(LAB, "Phenolphthalein is colourless in acid and turns which colour in alkali?", ["Pink", "Blue", "Green", "Black"], "A", "Phenolphthalein is a common acid-base indicator that turns pink in alkaline solution."),
    _item(LAB, "In the Gram stain, Gram-positive bacteria appear which colour?", ["Purple", "Pink", "Green", "Colourless"], "A", "Crystal violet is retained by Gram-positive cells, so they look purple. Gram-negative cells take up the pink counterstain."),
    _item(LAB, "Which chemical is the primary stain in the Gram staining procedure?", ["Crystal violet", "Safranin", "Methylene blue", "Malachite green"], "A", "The Gram stain uses crystal violet first, then iodine, a decolorizer, and safranin."),
    _item(LAB, "The oil-immersion objective of a light microscope is usually marked as", ["100x", "4x", "10x", "40x"], "A", "The 100x objective is used with immersion oil for bacterial smears. 4x, 10x and 40x are the lower-power dry objectives."),
    _item(LAB, "Which anticoagulant tube is used for a complete blood count?", ["EDTA tube", "Plain tube with no additive", "Fluoride-only glucose tube", "Sterile swab tube"], "A", "EDTA preserves cell shape, so it is the usual anticoagulant for haematology counts."),
    _item(LAB, "Sodium citrate is the anticoagulant of choice for which test group?", ["Coagulation tests", "Blood glucose only", "Urine sugar only", "Stool occult blood"], "A", "Citrate binds calcium and is used for tests such as prothrombin time."),
    _item(LAB, "Sodium fluoride is added to a blood sample mainly to", ["Stop glycolysis so glucose stays stable", "Stain the white cells", "Clot the sample faster", "Measure haemoglobin colour"], "A", "Fluoride inhibits glycolysis. Without it, cells keep using glucose and the reading falls."),
    _item(LAB, "A bacterial culture incubator is usually set near which temperature?", ["37°C", "4°C", "100°C", "121°C"], "A", "37°C is human body temperature and is the usual incubation temperature for many pathogenic bacteria."),
    _item(LAB, "The normal pH of human arterial blood is closest to", ["7.40", "2.00", "6.00", "9.00"], "A", "Blood is slightly alkaline. The normal range is about 7.35 to 7.45."),
    _item(LAB, "A usual haemoglobin range for a healthy adult male is", ["13 to 17 g/dL", "3 to 5 g/dL", "20 to 25 g/dL", "8 to 9 g/dL"], "A", "Adult male haemoglobin is generally about 13–17 g/dL. A much lower value suggests anaemia."),
    _item(LAB, "Ten percent neutral buffered formalin is used in a lab mainly as a", ["Tissue fixative", "Culture medium", "Anticoagulant", "pH indicator"], "A", "Formalin fixes tissue so its structure is preserved for later examination."),
    _item(LAB, "Which container is the usual choice for discarding contaminated needles?", ["Puncture-proof sharps box", "Open paper tray", "Ordinary waste bin", "Reagent bottle"], "A", "Needles and other sharps go into a puncture-proof sharps container, not into general waste."),
    _item(LAB, "A biosafety cabinet is used when the worker must", ["Handle infectious material with airflow protection", "Boil water for distillation", "Store flammable solvents only", "Weigh dry salts"], "A", "The cabinet's airflow protects both the sample and the worker during infectious work."),
    _item(LAB, "Distilled water is preferred for preparing reagents because it", ["Has very few dissolved salts", "Is always sterile acid", "Has a pH of 1", "Contains nutrients for bacteria"], "A", "Distillation removes most ions, so the water does not interfere with the reagent."),
    _item(LAB, "The hottest part of a properly adjusted Bunsen burner flame is", ["Just above the inner blue cone", "The yellow outer tip only", "The base of the burner tube", "The unburnt gas below the flame"], "A", "On a non-luminous blue flame, the hottest zone is just above the inner blue cone."),
    _item(PHY, "The SI unit of force is the", ["Newton", "Joule", "Watt", "Pascal"], "A", "Force is measured in newtons. The joule is energy, the watt is power, and the pascal is pressure."),
    _item(PHY, "Ohm's law relates voltage, current and resistance as", ["V = IR", "V = I / R", "V = R / I", "V = I + R"], "A", "Voltage equals current multiplied by resistance."),
    _item(PHY, "The SI unit of electric current is the", ["Ampere", "Volt", "Ohm", "Coulomb"], "A", "Current is measured in amperes. Potential difference is in volts and resistance in ohms."),
    _item(PHY, "Near the Earth's surface, the acceleration due to gravity is about", ["9.8 metres per second squared", "9.8 kilometres per second squared", "98 metres per second squared", "0.98 metres per second squared"], "A", "g is approximately 9.8 metres per second squared."),
    _item(PHY, "Newton's third law says that", ["Every action has an equal and opposite reaction", "A body stays at rest unless forced", "Force equals mass times acceleration", "Energy cannot be created"], "A", "The third law is the action-reaction pair. The first and second laws are the other two statements."),
    _item(PHY, "Kinetic energy of a moving body is", ["½ mv²", "mv", "mgh", "Fd"], "A", "Translational kinetic energy is one-half mass times speed squared. mgh is potential energy."),
    _item(PHY, "The SI unit of frequency is the", ["Hertz", "Newton", "Tesla", "Henry"], "A", "One hertz is one cycle per second."),
    _item(PHY, "The SI unit of power is the", ["Watt", "Joule", "Newton", "Volt"], "A", "Power is the rate of doing work and is measured in watts. The joule measures energy."),
    _item(PHY, "Sound waves cannot travel through", ["A vacuum", "Air", "Water", "Steel"], "A", "Sound needs a material medium. It travels in air, water and steel, but not in a vacuum."),
    _item(PHY, "The approximate speed of light in vacuum is", ["3 × 10⁸ m/s", "3 × 10⁶ m/s", "3 × 10⁴ m/s", "340 m/s"], "A", "Light in vacuum travels at about 3 × 10⁸ m/s. 340 m/s is roughly the speed of sound in air."),
    _item(PHY, "A convex lens is the usual lens in a microscope objective because it", ["Converges light to form a real image", "Always diverges light", "Blocks all light", "Measures electric current"], "A", "A convex lens brings rays to a focus, which is what an objective needs."),
    _item(PHY, "Electrical resistance is measured in", ["Ohms", "Amperes", "Watts", "Henries"], "A", "The ohm is the SI unit of resistance."),
    _item(CHEM, "The atomic number of an element equals its number of", ["Protons", "Neutrons only", "Electrons in the nucleus", "Molecules"], "A", "Atomic number is the proton count. In a neutral atom it also equals the electron count, but those electrons are outside the nucleus."),
    _item(CHEM, "A solution with pH 3 is", ["Acidic", "Neutral", "Strongly alkaline", "A pure metal"], "A", "pH below 7 is acidic, pH 7 is neutral, and pH above 7 is alkaline."),
    _item(CHEM, "The chemical formula of sulphuric acid is", ["H₂SO₄", "HCl", "HNO₃", "NaOH"], "A", "Sulphuric acid is H₂SO₄. HCl is hydrochloric acid, HNO₃ is nitric acid, and NaOH is sodium hydroxide."),
    _item(CHEM, "The chemical formula of ammonia is", ["NH₃", "CH₄", "CO₂", "H₂O"], "A", "Ammonia is NH₃. Methane is CH₄, carbon dioxide is CO₂, and water is H₂O."),
    _item(CHEM, "Avogadro's number is approximately", ["6.022 × 10²³", "6.022 × 10¹³", "3.0 × 10⁸", "9.8 × 10²"], "A", "One mole contains about 6.022 × 10²³ particles."),
    _item(CHEM, "Hardness of water is mainly due to dissolved salts of", ["Calcium and magnesium", "Sodium and potassium only", "Gold and silver", "Helium and neon"], "A", "Calcium and magnesium bicarbonates and sulphates make water hard."),
    _item(CHEM, "Diamond and graphite are allotropes of", ["Carbon", "Sulphur", "Phosphorus", "Oxygen"], "A", "Both diamond and graphite are forms of carbon with different structures."),
    _item(CHEM, "Oxidation in terms of electrons means", ["Loss of electrons", "Gain of electrons", "Gain of protons only", "Loss of neutrons"], "A", "Oxidation is loss of electrons. Reduction is gain of electrons."),
    _item(CHEM, "Isopropyl alcohol is commonly used in a lab as a", ["Disinfectant", "Strong mineral acid", "Anticoagulant", "Culture nutrient"], "A", "Isopropyl alcohol is used to disinfect skin and benches. It is not an anticoagulant or a culture medium."),
    _item(CHEM, "Water is often called the universal solvent because it", ["Dissolves a very wide range of substances", "Dissolves only metals", "Has pH 1", "Cannot form hydrogen bonds"], "A", "The polarity of water lets it dissolve many ionic and polar substances."),
    _item(CHEM, "The formula of table salt, sodium chloride, is", ["NaCl", "KCl", "CaCl₂", "Na₂CO₃"], "A", "Sodium chloride is NaCl. The other formulas are potassium chloride, calcium chloride and sodium carbonate."),
    _item(CHEM, "In a titration, the indicator is added to detect the", ["End point", "Boiling point", "Freezing point", "Melting point of the flask"], "A", "The colour change of the indicator marks the end point, close to the equivalence point."),
    _item(BIO, "Which cell organelle is called the powerhouse of the cell?", ["Mitochondrion", "Ribosome", "Golgi body", "Lysosome"], "A", "Mitochondria release energy as ATP. Ribosomes make proteins, the Golgi packages them, and lysosomes digest material."),
    _item(BIO, "In a eukaryotic cell, most of the DNA is located in the", ["Nucleus", "Cell wall", "Ribosome", "Centriole"], "A", "The nucleus holds the chromosomes. Ribosomes and centrioles do not store the genome."),
    _item(BIO, "Mitosis of one parent cell produces", ["Two genetically similar daughter cells", "Four haploid gametes", "One giant cell only", "No daughter cells"], "A", "Mitosis is for growth and repair and yields two daughter cells. Meiosis yields four haploid cells."),
    _item(BIO, "Meiosis is the division that produces", ["Gametes", "Identical body cells only", "Red blood cells only", "Bacteria"], "A", "Meiosis halves the chromosome number to form gametes."),
    _item(BIO, "Photosynthesis in a green plant takes place in the", ["Chloroplast", "Mitochondrion", "Nucleus", "Vacuole"], "A", "Chlorophyll in the chloroplast captures light. Mitochondria are for respiration."),
    _item(BIO, "Normal human body temperature is about", ["37°C", "27°C", "42°C", "98°C"], "A", "37°C is the usual core temperature. 98.6°F is the same point on the Fahrenheit scale, not 98°C."),
    _item(BIO, "Bacteria are classified as prokaryotes because they", ["Have no true nucleus", "Have a nucleus with many chromosomes", "Are always viruses", "Have chloroplasts"], "A", "A prokaryotic cell has no membrane-bound nucleus. Viruses are not cells."),
    _item(BIO, "Malaria is caused by", ["Plasmodium", "Mycobacterium", "Salmonella", "Vibrio"], "A", "Plasmodium, spread by the Anopheles mosquito, causes malaria. Mycobacterium causes tuberculosis."),
    _item(BIO, "Tuberculosis is caused by", ["Mycobacterium tuberculosis", "Plasmodium vivax", "Entamoeba histolytica", "Wuchereria bancrofti"], "A", "Mycobacterium tuberculosis is the usual cause of TB."),
    _item(BIO, "Typhoid fever is caused by", ["Salmonella Typhi", "Vibrio cholerae", "Plasmodium", "HIV"], "A", "Salmonella Typhi causes typhoid. Vibrio cholerae causes cholera."),
    _item(BIO, "Insulin is secreted by the", ["Pancreas", "Thyroid", "Adrenal medulla", "Pituitary"], "A", "Beta cells in the pancreatic islets secrete insulin, which lowers blood glucose."),
    _item(BIO, "Deficiency of vitamin C causes", ["Scurvy", "Rickets", "Beriberi", "Night blindness"], "A", "Vitamin C deficiency causes scurvy. Rickets is vitamin D, beriberi is thiamine, and night blindness is vitamin A."),
    _item(AGRI, "The three main paddy seasons of Kerala are", ["Virippu, Mundakan and Puncha", "Kharif, Rabi and Zaid only as north-Indian names", "Summer, monsoon and harvest with no local names", "Aus, Aman and Boro"], "A", "Kerala names the paddy seasons Virippu, Mundakan and Puncha."),
    _item(AGRI, "Urea is used as a fertilizer mainly because it supplies", ["Nitrogen", "Phosphorus", "Potassium", "Calcium"], "A", "Urea contains about 46 percent nitrogen. Phosphorus and potassium come from other fertilizers."),
    _item(AGRI, "The letters N, P and K on a fertilizer bag stand for", ["Nitrogen, phosphorus and potassium", "Nitrate, protein and calcium", "Sodium, potash and lime", "Nickel, platinum and copper"], "A", "N-P-K is the standard label for nitrogen, phosphorus and potassium."),
    _item(AGRI, "Rhizobium bacteria in the root nodules of legumes mainly", ["Fix atmospheric nitrogen", "Cause wilt disease", "Produce phosphorus", "Kill earthworms"], "A", "Rhizobium converts atmospheric nitrogen into a form the legume can use."),
    _item(AGRI, "Vermicompost is produced with the help of", ["Earthworms", "Honey bees", "Silkworms", "Fish only"], "A", "Earthworms break down organic waste into vermicompost."),
    _item(AGRI, "Drip irrigation is preferred in many gardens because it", ["Delivers water near the root and reduces waste", "Floods the whole field", "Uses only rainwater stored in tanks", "Replaces the need for soil"], "A", "Drip lines wet the root zone, so less water is lost than in flood irrigation."),
    _item(AGRI, "A Gunter's chain used in old land survey measures", ["66 feet", "100 metres", "33 metres", "10 feet"], "A", "A Gunter's chain is 66 feet long and has 100 links."),
    _item(AGRI, "A metric survey chain commonly used in the field is", ["20 metres", "1 metre", "100 feet", "5 centimetres"], "A", "Metric chains are commonly 20 m or 30 m long."),
    _item(AGRI, "A cross-staff is used in chain surveying to", ["Set out a right angle", "Measure the height of a hill", "Find the magnetic north only", "Weigh crop samples"], "A", "The open cross-staff lets the surveyor set a perpendicular offset."),
    _item(AGRI, "Cardamom cultivation in Kerala is concentrated mainly in", ["Idukki", "Alappuzha backwaters", "The coastal sand of Kollam", "The city of Thiruvananthapuram"], "A", "The high ranges of Idukki are the main cardamom area of Kerala."),
    _item(AGRI, "Black pepper, coconut and rubber are important crops of", ["Kerala", "Rajasthan desert districts", "Ladakh", "The Thar region"], "A", "Plantation crops such as pepper, coconut and rubber are central to Kerala's agriculture."),
    _item(AGRI, "Mulching a crop bed is done mainly to", ["Reduce evaporation and weed growth", "Increase soil erosion", "Wash away fertilizer", "Stop all rainfall from entering"], "A", "A mulch cover keeps moisture in and suppresses weeds."),
    _item(AGRI, "Organic farming avoids the routine use of", ["Synthetic chemical fertilizers and pesticides", "Compost and green manure", "Crop rotation", "Local seed varieties"], "A", "Organic practice relies on compost, manure and biological control rather than synthetic agrochemicals."),
    _item(AGRI, "Green manuring means ploughing in a crop such as sunn hemp in order to", ["Add organic matter and nutrients to the soil", "Harvest grain for sale", "Kill all soil organisms", "Measure the field with a chain"], "A", "A green-manure crop is grown and turned into the soil to improve fertility."),
    _item(AGRI, "The Village Field Assistant post in Category 571/2025 is under the", ["Revenue department", "Health Services department", "Fire and Rescue Services", "Kerala Police"], "A", "The October 2026 VFA examination is a Revenue department recruitment."),
    _item(AGRI, "Soil pH most suitable for a large number of field crops is around", ["6 to 7", "2 to 3", "11 to 12", "1 to 2"], "A", "Most crops prefer slightly acid to neutral soil, around pH 6–7."),
    _item(AGRI, "A biofertilizer differs from a bag of chemical fertilizer because it", ["Uses living cultures to supply nutrients", "Is only a painted sack", "Is a harvesting sickle", "Is a unit of land area"], "A", "Biofertilizers such as Rhizobium preparations supply nutrients through living cultures."),
    _item(AGRI, "In a coconut garden, the main harvested product used for oil is the", ["Kernel of the mature nut", "Tender leaf only", "Root bark", "Male flower dust"], "A", "Copra is the dried kernel, and coconut oil is extracted from it."),
    _item(AGRI, "Rubber latex is collected from the tree by", ["Tapping the bark", "Cutting the main root", "Shaking the leaves", "Boring the trunk like a well"], "A", "A thin cut in the bark lets latex flow into a cup. This is tapping."),
    _item(AGRI, "Excessive use of nitrogenous fertilizer without balance often causes", ["Lush leafy growth and lodging", "Immediate death of all soil", "Conversion of the field into rock", "Complete stoppage of photosynthesis"], "A", "Too much nitrogen pushes soft vegetative growth, and cereals may lodge."),
    _item(ENGINE, "The four strokes of a four-stroke engine, in order, are", ["Intake, compression, power, exhaust", "Power, intake, exhaust, compression", "Exhaust, power, intake, compression", "Compression, exhaust, power, intake"], "A", "The piston draws the charge, compresses it, delivers power, then pushes out the exhaust."),
    _item(ENGINE, "A diesel engine ignites the fuel by", ["Heat of compression", "A spark plug", "A glow of the headlamp", "Friction of the clutch"], "A", "Diesel engines are compression-ignition engines. Petrol engines use a spark plug."),
    _item(ENGINE, "A petrol engine ignites the mixture by", ["A spark plug", "Compression heat alone", "The radiator fan", "The brake shoe"], "A", "A spark-ignition engine fires the petrol-air mixture with a spark plug."),
    _item(ENGINE, "The crankshaft of an engine converts", ["Up-and-down piston motion into rotation", "Rotation into electric current", "Brake fluid pressure into heat", "Steering angle into toe"], "A", "The connecting rod and crank throw turn the piston's reciprocating motion into crankshaft rotation."),
    _item(ENGINE, "The camshaft in an engine mainly", ["Opens and closes the valves", "Charges the battery", "Pumps the brake fluid", "Measures the fuel level"], "A", "Cam lobes push the valves open in time with the crankshaft."),
    _item(ENGINE, "Piston rings are fitted mainly to", ["Keep combustion gas in and control oil", "Hold the gudgeon pin only", "Paint the piston crown", "Balance the crank web"], "A", "Compression rings keep the gases in. The oil ring scrapes excess oil from the cylinder wall."),
    _item(ENGINE, "The flywheel is fitted to the crankshaft in order to", ["Smooth the power impulses", "Filter the engine oil", "Cool the coolant", "Adjust the toe-in"], "A", "The flywheel stores energy during the power stroke and carries the engine through the other strokes."),
    _item(ENGINE, "In an older petrol engine, the carburettor", ["Mixes air and petrol", "Injects diesel at high pressure", "Charges the battery", "Locks the wheels"], "A", "The carburettor meters petrol into the incoming air. Diesel engines use an injection pump and injectors."),
    _item(ENGINE, "A diesel fuel injector", ["Sprays fuel into the combustion chamber", "Produces the ignition spark", "Cools the engine", "Operates the clutch pedal"], "A", "The injector atomizes diesel so it can burn in the hot compressed air."),
    _item(ENGINE, "MPFI in a petrol engine means", ["Multi-point fuel injection", "Manual petrol flow indicator", "Main piston friction index", "Motor pump fan impeller"], "A", "Multi-point fuel injection places an injector at each intake port."),
    _item(ENGINE, "The octane number of petrol indicates its", ["Resistance to knocking", "Viscosity in winter", "Freezing point", "Colour in the tank"], "A", "A higher octane number means the petrol resists knocking. Cetane number is the diesel equivalent for ignition quality."),
    _item(ENGINE, "The cetane number of diesel indicates its", ["Ignition quality", "Octane rating", "Battery voltage", "Tyre size"], "A", "A higher cetane number means the diesel ignites more readily after injection."),
    _item(BRAKE, "The clutch is placed between the engine and the gearbox so that it can", ["Connect or disconnect the drive", "Cool the coolant", "Generate electricity", "Measure wheel alignment"], "A", "Disengaging the clutch lets the driver change gear without forcing the gears."),
    _item(BRAKE, "A differential in the driving axle lets the", ["Outer wheel rotate faster than the inner wheel on a turn", "Engine stop while the car moves", "Brake fluid boil", "Steering wheel lock"], "A", "On a bend the outer wheel travels farther, so the differential allows different wheel speeds."),
    _item(BRAKE, "Hydraulic brakes transmit force from the pedal through", ["Brake fluid", "Engine oil from the sump", "Coolant from the radiator", "Air from the tyre"], "A", "The master cylinder pressurizes brake fluid, and wheel cylinders or calipers apply the shoes or pads."),
    _item(BRAKE, "The master cylinder in a hydraulic brake system", ["Produces the fluid pressure", "Filters the petrol", "Charges the battery", "Opens the engine valves"], "A", "Pedal force on the master-cylinder piston creates the hydraulic pressure."),
    _item(BRAKE, "A gearbox is used mainly to", ["Provide different torque and speed ratios", "Sterilize the fuel", "Measure the camber", "Store coolant"], "A", "Lower gears multiply torque for starting and hills. Higher gears allow road speed."),
    _item(BRAKE, "ABS on a vehicle is designed to", ["Stop the wheels from locking during braking", "Increase the engine compression", "Replace the clutch", "Inflate the tyres"], "A", "Anti-lock braking releases and reapplies brake pressure so the driver can still steer."),
    _item(BRAKE, "A disc brake applies friction by squeezing the disc with", ["Pads in a caliper", "A band around the flywheel", "The clutch plate", "The radiator fan"], "A", "The caliper presses pads against the rotating disc."),
    _item(BRAKE, "The clutch plate is faced with friction material so that it can", ["Transmit torque without slipping once engaged", "Cool the engine", "Conduct brake fluid", "Generate a spark"], "A", "The friction lining locks the driven plate to the flywheel when the clutch is engaged."),
    _item(STEER, "Toe-in means that the", ["Front edges of the front wheels are closer than the rear edges", "Wheels are tilted outward at the top", "Steering axis is vertical", "Rear axle is removed"], "A", "Toe-in is a small inward set of the front wheels, measured at hub height."),
    _item(STEER, "Camber is the", ["Inward or outward tilt of the wheel from the vertical", "Gap in the spark plug", "Level of engine oil", "Length of the propeller shaft"], "A", "Camber is viewed from the front. Positive camber tilts the top of the wheel outward."),
    _item(STEER, "Caster is the", ["Fore-and-aft tilt of the steering axis", "Colour of the brake fluid", "Gap of the piston ring", "Pressure in the fuel tank"], "A", "Caster is the tilt of the kingpin or steering axis, and it helps the wheels self-centre."),
    _item(STEER, "A hydraulic shock absorber is fitted to", ["Damp the spring movement", "Increase fuel octane", "Charge the battery", "Open the exhaust valve"], "A", "The damper controls bounce so the spring does not keep oscillating."),
    _item(STEER, "Kingpin inclination is part of", ["Steering geometry", "The fuel injection pump", "The lubrication chart", "The lighting circuit"], "A", "Kingpin inclination, camber, caster and toe are the main steering-geometry angles."),
    _item(STEER, "Wheel alignment is checked mainly to", ["Reduce tyre wear and keep the vehicle tracking straight", "Increase engine compression", "Change the gear ratio", "Cool the brakes"], "A", "Wrong toe or camber scrubs the tyres and pulls the vehicle to one side."),
    _item(COOL, "The radiator in a liquid-cooled engine", ["Gives up heat from the coolant to the air", "Mixes diesel and air", "Stores brake fluid", "Generates the spark"], "A", "Hot coolant from the engine passes through the radiator core, and airflow removes the heat."),
    _item(COOL, "The thermostat in the cooling system", ["Opens when the coolant is hot enough", "Always blocks the radiator", "Replaces the water pump", "Measures engine oil pressure"], "A", "A closed thermostat lets the engine warm up. It opens to send coolant through the radiator."),
    _item(COOL, "The water pump in a cooling system", ["Circulates coolant through the engine and radiator", "Pumps petrol to the carburettor only", "Pumps air into the tyres", "Drains the gearbox"], "A", "The pump keeps coolant moving so heat is carried to the radiator."),
    _item(COOL, "Engine oil is circulated by the", ["Oil pump", "Fuel injector", "Brake master cylinder", "Horn relay"], "A", "The oil pump picks up oil from the sump and feeds the bearings."),
    _item(COOL, "An SAE grade such as 20W-40 on an oil can refers to", ["Viscosity", "Octane number", "Cetane number", "Battery capacity"], "A", "SAE viscosity grades describe how the oil flows when cold and when hot."),
    _item(COOL, "Ethylene glycol is added to engine coolant mainly to", ["Lower the freezing point and raise the boiling point", "Increase the octane number", "Lubricate the clutch", "Charge the battery"], "A", "The glycol mix protects the cooling system in both cold and hot weather."),
    _item(ELEC, "While the engine is running, the battery is charged by the", ["Alternator", "Starter motor", "Horn", "Fuel gauge"], "A", "The alternator generates current and the regulator controls the charging voltage."),
    _item(ELEC, "The usual electrical system of a car uses a battery of about", ["12 volts", "1.5 volts", "220 volts", "440 volts"], "A", "Light vehicles use a 12-volt lead-acid battery. 220 volts is household mains."),
    _item(ELEC, "The electrolyte in a conventional lead-acid battery is", ["Dilute sulphuric acid", "Engine oil", "Petrol", "Distilled brake fluid only"], "A", "The cells contain dilute sulphuric acid and lead plates."),
    _item(ELEC, "The starter motor is used to", ["Crank the engine until it fires", "Charge the battery continuously", "Operate the windscreen washer only", "Measure the toe-in"], "A", "The starter turns the flywheel ring gear. After the engine fires, the starter is switched off."),
    _item(ELEC, "A fuse in a vehicle circuit is meant to", ["Melt and open the circuit if current is too high", "Increase the current", "Store the charge", "Replace the battery"], "A", "The fuse is the weak link that protects the wiring from an overload."),
    _item(ELEC, "A glow plug is fitted on many diesel engines to", ["Heat the chamber for a cold start", "Ignite every power stroke like a spark plug", "Charge the battery", "Pump the coolant"], "A", "The glow plug preheats the combustion chamber. It is not the ignition source on every stroke."),
    _item(ELEC, "A spark plug is a part of", ["A petrol engine ignition system", "A diesel injection pump", "The cooling radiator", "The differential"], "A", "The plug jumps a spark in the petrol cylinder. Diesel engines do not use a spark plug for normal running."),
    _item(ELEC, "Headlamp and other vehicle lamps are part of the", ["Lighting circuit", "Fuel injection pump", "Clutch housing", "Oil sump"], "A", "Lamps, switches and fuses form the lighting circuit, fed from the battery and alternator."),
]


def _spread_answers(items):
    """Move the correct choice around A–D so a paper is not all answer A."""
    letters = ("A", "B", "C", "D")
    spread = []
    for index, item in enumerate(items):
        target = letters[index % 4]
        options = item["options"]
        correct_text = options[item["correct_answer"]]
        others = [options[letter] for letter in letters if options[letter] != correct_text]
        ordered = []
        other_index = 0
        for letter in letters:
            if letter == target:
                ordered.append(correct_text)
            else:
                ordered.append(others[other_index])
                other_index += 1
        spread.append({
            **item,
            "options": {letters[i]: ordered[i] for i in range(4)},
            "correct_answer": target,
        })
    return spread


from questionbank.syllabus_mcqs_extra import EXTRA_MCQS

SYLLABUS_MCQS = _spread_answers(SYLLABUS_MCQS + EXTRA_MCQS)
