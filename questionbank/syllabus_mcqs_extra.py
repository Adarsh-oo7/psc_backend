"""Extra syllabus MCQs for sections that had no exam-specific questions.

Stems are unique. Each item has four choices of the same kind.
The loader attaches an item only to exams whose syllabus uses that topic.
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
AUTO = "Auto Electrical"

LINE_BASIC = "Basic Electricity"
LINE_OHM = "Ohm's Law and Circuits"
LINE_LINE = "Overhead Lines and Safety"
LINE_TR = "Transformers and Distribution"
LINE_EARTH = "Instruments and Earthing"

E_BASIC = "Basic Electricity — Fundamentals, Resistance, Conductors, Wires"
E_OHM = "Ohm's Law — Kirchhoff's Law, Temperature Effects, Cell Types"
E_MAG = "Magnetism — Properties, Electromagnetism, Fleming's Rules, Faraday's Laws"
E_AC = "Alternating Current and Earthing — AC, Earthing, Wiring, Megger"
E_DC = "DC Machines — Generators, DC Motors, Starters"
E_MOT = "AC Motors — Single & 3 Phase, DOL, Star-Delta Starters"
E_INST = "Instruments and Transformers — Measuring Instruments, EMF Equation"
E_LAMP = "Illumination and Electronics — Lamps, Semiconductors, Diodes, Transistors"
E_GEN = "Power Generation — Energy Sources, Types of Power Generation"
E_TD = "Transmission and Distribution — AC vs DC Comparison"

ANATOMY = "Anatomy and Physiology"
NURSING = "Fundamentals of Nursing"
COMMUNITY = "Community Health and First Aid"
FIRE = "Fire and Rescue Special Topics"
EXCISE = "Excise Special Topics"
BRANCH = "Special Branch and Police Topics"
FOREST = "Forest and Wildlife Special Topics"
BAND = "Band Music and Police Special Topics"
ENGMATH = "Engineering Maths"
DRAWING = "Basic Engineering and Drawing"
LAWS = "Important Laws"
ARTS = "Arts Culture Literature Sports"
ECON = "Economics"

ROWS = [
    # --- Shared science, still thin on several papers ---
    (LAB, "A fume hood in a laboratory is used mainly to", ["Carry away harmful vapours while you work", "Incubate bacterial cultures", "Spin blood samples", "Store flammable solvents on the bench"], "A", "The hood draws vapours away from the worker. It is not an incubator or a centrifuge."),
    (LAB, "Mouth pipetting of a reagent is avoided because it", ["Can let the chemical enter the mouth", "Makes the reading more accurate", "Sterilizes the pipette", "Is required for a blood count"], "A", "A pipette filler or bulb is used. Drawing liquid by mouth can cause poisoning or infection."),
    (LAB, "The usual personal protection for a wet chemistry bench includes", ["A coat, eye protection and gloves", "Only an open-toed sandal", "A stethoscope and a torch", "A welding shield alone"], "A", "The coat, goggles and gloves protect skin and eyes from splashes."),
    (LAB, "On a light microscope, the fine-focus knob is used to", ["Sharpen the image after the coarse focus", "Change the objective power by itself", "Heat the slide", "Count the cells automatically"], "A", "Coarse focus finds the specimen. Fine focus then makes the image sharp."),
    (LAB, "A wet mount of a specimen is finished by placing", ["A cover slip over the drop", "The slide inside an autoclave", "Oil on the eyepiece", "The specimen in a sharps box"], "A", "The cover slip flattens the drop so it can be viewed and does not dry at once."),
    (PHY, "The law of reflection says that the angle of incidence", ["Equals the angle of reflection", "Is always twice the angle of reflection", "Is always zero", "Equals the focal length"], "A", "On a plane mirror the incident and reflected rays make equal angles with the normal."),
    (PHY, "When resistors are joined in series, the total resistance", ["Is the sum of the individual resistances", "Is always smaller than the smallest one", "Becomes zero", "Equals the current"], "A", "Series resistances add. The same current passes through each of them."),
    (PHY, "Work done by a force is the product of", ["Force and displacement in the direction of the force", "Mass and velocity only", "Current and resistance only", "Frequency and wavelength only"], "A", "Work equals force times the displacement along the force. The unit is the joule."),
    (PHY, "Momentum of a moving body is", ["Mass multiplied by velocity", "Mass divided by time", "Force divided by area", "Energy divided by power"], "A", "Momentum is mass times velocity. A heavier or faster body has more momentum."),
    (CHEM, "A solution of pH 7 is", ["Neutral", "Strongly acidic", "Strongly alkaline", "A solid metal"], "A", "pH 7 is neutral. Values below 7 are acidic and values above 7 are alkaline."),
    (CHEM, "Passing carbon dioxide through lime water makes the water", ["Milky", "Deep blue", "Remain perfectly clear in every case", "Turn into a metal"], "A", "Carbon dioxide forms insoluble calcium carbonate, which makes lime water look milky."),
    (CHEM, "Rusting of iron produces mainly", ["Hydrated iron oxide", "Pure gold", "Sodium chloride", "Nitrogen gas only"], "A", "Iron reacts with oxygen and moisture to form the reddish hydrated oxide called rust."),
    (CHEM, "A catalyst in a chemical reaction", ["Speeds the reaction and is not used up", "Is the product that is collected", "Stops every reaction", "Changes into the solvent"], "A", "The catalyst provides an easier path and can be recovered at the end."),
    (BIO, "Red blood cells carry oxygen mainly with the help of", ["Haemoglobin", "Insulin", "Bile", "Keratin"], "A", "Haemoglobin in the red cells binds oxygen in the lungs and releases it in the tissues."),
    (BIO, "Platelets in the blood help mainly in", ["Clotting", "Carrying oxygen over long distances", "Producing bile", "Absorbing fat"], "A", "Platelets start the clot that stops bleeding. Red cells carry oxygen."),
    (BIO, "The functional filtering unit of the kidney is the", ["Nephron", "Alveolus", "Neuron", "Osteon"], "A", "Each nephron filters blood and forms urine. Alveoli are in the lung and neurons are nerve cells."),
    (BIO, "Dengue spreads through the bite of", ["Aedes mosquitoes", "House flies only", "Earthworms", "Honey bees"], "A", "Aedes aegypti is the usual dengue vector. It breeds in clean stored water."),
    (AGRI, "Pepper is traditionally called the king of spices and is a major crop of", ["Kerala", "The Rajasthan desert", "Ladakh", "The Indo-Gangetic salt flats"], "A", "Black pepper from Kerala has long been the leading spice export of the state."),
    (AGRI, "A large share of India's natural rubber comes from", ["Kerala", "Punjab wheat belt", "Rajasthan", "Sikkim only"], "A", "Kottayam and neighbouring districts are the heart of Kerala's rubber plantations."),
    (AGRI, "Grafting in horticulture is done to", ["Join a desired shoot to a strong rootstock", "Measure a field with a chain", "Dry copra in the sun", "Tap rubber latex"], "A", "The scion keeps the fruit variety. The rootstock supplies the roots."),
    (AGRI, "Contour bunds on a slope are built mainly to", ["Slow runoff and reduce soil loss", "Increase the speed of rainwater", "Replace all crops with plastic", "Stop earthworms"], "A", "Bunds along the contour hold water and soil on the slope."),
    (AGRI, "A Krishi Vigyan Kendra is", ["A farm science centre for training farmers", "A revenue village office", "A police station", "A fire station"], "A", "KVKs demonstrate new practices and train farmers in each district."),
    (AGRI, "Crop rotation helps the field because it", ["Breaks pest cycles and balances nutrient use", "Grows the same crop every season on purpose", "Removes all organic matter", "Stops rainfall"], "A", "Changing the crop from season to season reduces pests and uses nutrients more evenly."),
    (ECON, "The Reserve Bank of India is the country's", ["Central bank", "Stock exchange", "State public service commission", "Village panchayat"], "A", "The RBI issues currency notes and manages monetary policy. Coins are issued by the Government of India."),
    (ECON, "GST in India is a tax on", ["Goods and services", "Only agricultural land", "Only imports of gold coins from one mint", "Only salaries of panchayat members"], "A", "Goods and Services Tax replaced many central and state indirect taxes."),
    (ECON, "Inflation means", ["A general rise in prices", "A fall in every price forever", "The area of a farm", "The number of districts"], "A", "Inflation is a sustained rise in the general price level, so money buys less."),
    (ECON, "Gross domestic product measures the value of", ["Final goods and services produced in the country", "Only the gold in the reserve", "Only exports of spices", "Only coins in circulation"], "A", "GDP is the market value of final output produced within the country in a period."),
    (ECON, "NITI Aayog replaced the", ["Planning Commission", "Election Commission", "Supreme Court", "Reserve Bank"], "A", "The Planning Commission was replaced by NITI Aayog in 2015."),
    (ECON, "Agriculture, forestry and fishing belong to the", ["Primary sector", "Tertiary sector only", "Foreign sector only", "Insurance sector only"], "A", "The primary sector uses natural resources directly. Services are the tertiary sector."),
    (LAWS, "The Right to Information Act was passed in", ["2005", "1950", "1947", "2019"], "A", "The RTI Act, 2005, gives citizens a right to seek information from public authorities."),
    (LAWS, "POCSO is the law that protects children from", ["Sexual offences", "Only traffic fines", "Only income tax", "Only land survey errors"], "A", "The Protection of Children from Sexual Offences Act deals with sexual offences against children."),
    (LAWS, "The Consumer Protection Act, 2019, provides for", ["Redress of consumer complaints", "Army recruitment only", "Forest settlement only", "Electricity generation only"], "A", "Consumer commissions hear complaints about defective goods and deficient services."),
    (LAWS, "The Right of Children to Free and Compulsory Education Act provides for", ["Free elementary education", "Free university education abroad", "Free electricity for factories", "Free rail travel for all adults"], "A", "The RTE Act, 2009, provides free and compulsory education for children in the elementary stage."),
    (ARTS, "Kathakali is a classical dance-drama of", ["Kerala", "Punjab", "Manipur only", "Rajasthan only"], "A", "Kathakali uses stories from the epics, elaborate makeup and a sung text."),
    (ARTS, "Mohiniyattam is a classical dance form of", ["Kerala", "Tamil Nadu's Bharatanatyam tradition alone", "Assam", "Kashmir"], "A", "Mohiniyattam is the graceful classical dance of Kerala, performed to Sopana music."),
    (ARTS, "Theyyam is a ritual art mainly of", ["North Kerala", "The Thar desert", "Coastal Odisha only", "Ladakh monasteries"], "A", "Theyyam is performed in the sacred groves and shrines of north Kerala."),
    (ARTS, "Jana Gana Mana was written by", ["Rabindranath Tagore", "Bankim Chandra Chatterjee", "Mohammad Iqbal", "Sarojini Naidu"], "A", "Tagore wrote Jana Gana Mana, which is the national anthem. Bankim wrote Vande Mataram."),
    (ARTS, "The Olympic symbol is", ["Five interlocking rings", "A single star", "A lotus and a wheel only", "Two crossed swords"], "A", "The five rings stand for the inhabited continents that take part in the Games."),
    # --- Lineman ---
    (LINE_BASIC, "An electric current is a flow of", ["Charge", "Neutral atoms only", "Sound", "Heat with no charge"], "A", "Current is the movement of electric charge, usually electrons in a metal."),
    (LINE_BASIC, "Copper and aluminium are used as conductors because they", ["Let current pass easily", "Block every current", "Are the best insulators", "Cannot be drawn into wire"], "A", "Both metals have low resistance, so they are drawn into cable and overhead conductor."),
    (LINE_BASIC, "Rubber, porcelain and dry PVC are used as", ["Insulators", "The best conductors", "Fuse elements", "Earth electrodes by themselves"], "A", "These materials resist the flow of current and support or cover live parts."),
    (LINE_BASIC, "If a wire is made longer, and nothing else changes, its resistance", ["Increases", "Falls to zero", "Becomes the supply frequency", "Stays unrelated to length"], "A", "Resistance is proportional to length and inversely proportional to the area of the cross-section."),
    (LINE_BASIC, "A thicker wire of the same metal and length has", ["Lower resistance", "Higher resistance", "No resistance at all", "The same resistance as a hair-thin wire"], "A", "A larger cross-section gives the current more paths, so resistance falls."),
    (LINE_BASIC, "The SI unit of electric charge is the", ["Coulomb", "Newton", "Joule", "Hertz"], "A", "Charge is measured in coulombs. Current in amperes is charge passing per second."),
    (LINE_OHM, "In a series circuit the current through each element is", ["The same", "Always different and unrelated", "Zero at the source", "Equal to the voltage of each element"], "A", "There is only one path, so the same current flows through every series element."),
    (LINE_OHM, "Across elements joined in parallel, the voltage is", ["The same", "Always zero", "Added like resistors in series", "Equal to the current"], "A", "Parallel branches share the same two nodes, so each branch sees the same voltage."),
    (LINE_OHM, "Kirchhoff's current law says that at a junction the algebraic sum of currents is", ["Zero", "Always equal to the voltage", "Always equal to the resistance", "Infinite"], "A", "Current entering a node equals current leaving it, so the signed sum is zero."),
    (LINE_OHM, "Kirchhoff's voltage law says that around a closed loop the algebraic sum of voltages is", ["Zero", "Equal to the frequency", "Equal to the number of wires", "Always the highest voltage only"], "A", "The rises and drops of potential around a loop cancel."),
    (LINE_OHM, "A dry cell used in a torch is normally treated as a", ["Primary cell that is not recharged in service", "Secondary cell that is routinely recharged", "Transformer", "Fuse"], "A", "A primary cell is used until it is spent. A lead-acid or lithium battery is a secondary cell."),
    (LINE_OHM, "For a pure metal, raising the temperature usually", ["Increases its resistance", "Reduces its resistance to zero at once", "Turns it into an insulator oil", "Has no effect of any kind"], "A", "The resistance of pure metals rises with temperature. Carbon and many semiconductors do the opposite."),
    (LINE_LINE, "Before a lineman works on a dead overhead line, the line should be", ["Isolated, tested and earthed", "Left live to save time", "Painted only", "Shorted to the phase on purpose while live"], "A", "Isolation, a voltage test and a local earth protect the worker if the line is re-energised by mistake."),
    (LINE_LINE, "A safety belt and a secured ladder are used so that the worker", ["Cannot fall while working aloft", "Can increase the line voltage", "Can replace the earth wire with a phase", "Need not wear a helmet"], "A", "Fall protection is part of pole and tower work, together with a helmet and gloves."),
    (LINE_LINE, "The sag of an overhead conductor is provided so that the wire", ["Is not over-tensioned when it contracts in the cold", "Touches the ground at mid-span", "Carries no current", "Replaces the pole"], "A", "Sag lets the conductor expand and contract. Too little sag can snap the wire in cold weather."),
    (LINE_LINE, "A stay or guy wire on a pole is used to", ["Balance the pull of the line", "Carry the load current", "Measure insulation", "Replace the cross-arm"], "A", "The stay takes the mechanical pull at an angle or a terminal pole. It is not the power conductor."),
    (LINE_LINE, "Minimum clearance of a low-voltage line above a road is kept so that", ["Vehicles and people do not touch the live wire", "The wire can lie on the road", "Birds cannot see it", "Rain cannot fall"], "A", "Statutory clearance keeps traffic and people away from the conductor."),
    (LINE_TR, "A distribution transformer supplies consumers at", ["A lower, usable voltage", "The generating-station voltage with no change", "Only direct current", "Radio frequency"], "A", "The distribution transformer steps the feeder voltage down to the voltage used in homes and shops."),
    (LINE_TR, "A transformer works on the principle of", ["Mutual induction", "Ohm's law alone with no changing flux", "Chemical action in a cell", "Heating of a fuse"], "A", "A changing current in the primary induces a voltage in the secondary."),
    (LINE_TR, "A step-down transformer has", ["More turns on the primary than on the secondary", "More turns on the secondary than on the primary", "No windings", "Only one solid bar of copper"], "A", "Fewer secondary turns give a lower secondary voltage. A step-up transformer is the reverse."),
    (LINE_TR, "An ordinary transformer does not transfer energy from a steady", ["Direct current", "Alternating current", "Changing flux", "Alternating voltage"], "A", "A steady direct current produces no changing flux, so no voltage is induced in the secondary."),
    (LINE_EARTH, "Earthing a metal cover of equipment gives fault current", ["A safe path into the ground", "A path through the user", "No path at all", "A path into the water pipe only when the pipe is removed"], "A", "If a live wire touches the cover, the earth wire carries the fault current and the protective device opens."),
    (LINE_EARTH, "A Megger is used to measure", ["Insulation resistance", "The mechanical sag of a span", "The oil level", "The speed of a ceiling fan only"], "A", "The Megger applies a high test voltage and reads how well the insulation resists leakage."),
    (LINE_EARTH, "In a correct wiring system the earth conductor is coloured", ["Green, or green with a yellow stripe", "Plain red in every new Indian installation", "Bare copper left as the phase", "White only, with no other rule"], "A", "Green or green-yellow identifies the protective earth. It must not be used as a phase or neutral."),
    (LINE_EARTH, "A fuse or a breaker is placed in the", ["Phase or live conductor", "Earth conductor only", "Stay wire", "Neutral only, never in the phase"], "A", "Opening the live conductor disconnects the supply. A fuse in the earth path would be dangerous."),
    # --- Electrician (longer official titles; different stems) ---
    (E_BASIC, "Free electrons in a metal are what move when the metal", ["Carries a current", "Is used as a perfect insulator", "Is a piece of dry wood", "Is a rubber glove"], "A", "Metals conduct because some electrons are free to drift when a voltage is applied."),
    (E_BASIC, "Resistance of a conductor depends on its material, its length and its", ["Cross-sectional area", "Colour of the insulation only", "Brand name only", "The day of the week"], "A", "Resistivity, length and area fix the resistance. Insulation colour is only identification."),
    (E_BASIC, "Nichrome is used in heating elements because it", ["Has high resistance and withstands heat", "Is the best conductor known", "Melts at room temperature", "Is an insulator"], "A", "The high-resistance alloy turns electrical energy into heat without burning away at once."),
    (E_BASIC, "Stranded conductor is preferred for flexible leads because it", ["Bends without breaking as easily as one solid wire", "Has no resistance", "Cannot carry current", "Is always an earth rod"], "A", "Many fine strands flex. A single thick wire of the same area is stiffer."),
    (E_OHM, "If the voltage across a resistor is doubled and the resistance stays the same, the current", ["Doubles", "Becomes zero", "Stays exactly the same", "Reverses the unit of resistance"], "A", "From V = IR, current is proportional to voltage when resistance is constant."),
    (E_OHM, "A secondary cell differs from a primary cell because it", ["Can be recharged", "Can never be recharged", "Produces sound instead of voltage", "Has no terminals"], "A", "Lead-acid and lithium batteries are secondary cells. A simple dry cell is primary."),
    (E_OHM, "The temperature coefficient of resistance of a pure metal is", ["Positive", "Always negative", "Always zero", "Meaningless"], "A", "A positive coefficient means resistance rises as the metal gets hotter."),
    (E_OHM, "Two equal resistors in parallel have a combined resistance equal to", ["Half of one of them", "The sum of both", "Zero", "Twice one of them"], "A", "Equal parallel resistors share current, and the combination equals half of either resistor."),
    (E_MAG, "Like magnetic poles", ["Repel", "Always attract", "Do nothing", "Produce light"], "A", "Like poles repel and unlike poles attract."),
    (E_MAG, "Fleming's left-hand rule is used for the", ["Force on a current-carrying conductor", "Direction of induced current in a generator", "Colour code of resistors", "Value of a fuse"], "A", "The left-hand rule gives the direction of force, which is the motor effect."),
    (E_MAG, "Fleming's right-hand rule is used for the", ["Direction of induced current", "Force on a motor conductor", "Size of an insulator", "Colour of the earth wire"], "A", "The right-hand rule relates motion, field and induced current in a generator."),
    (E_MAG, "Faraday's law says the induced voltage is proportional to the", ["Rate of change of magnetic flux", "Colour of the magnet", "Length of the stay wire", "Steady flux that never changes"], "A", "A faster change of flux induces a larger voltage. A perfectly steady flux induces nothing."),
    (E_AC, "In India the usual supply frequency is", ["50 hertz", "60 hertz", "25 hertz", "400 hertz"], "A", "The public supply in India is 50 hertz. 60 hertz is used in some other countries."),
    (E_AC, "Alternating current differs from direct current because it", ["Reverses direction periodically", "Never changes direction", "Is always a chemical current in a dry cell", "Has no frequency"], "A", "An alternating current rises, falls and reverses. A direct current keeps one direction."),
    (E_AC, "A Megger test on a healthy winding should show", ["A high insulation resistance", "A dead short", "Zero ohms in every case", "The speed of the motor"], "A", "Good insulation reads high on the Megger. A very low reading means the insulation has failed."),
    (E_AC, "The protective earth in a wiring system is connected to", ["The metal body of the appliance", "The live terminal of the lamp on purpose", "The fuse wire as a load", "Nothing at all"], "A", "The earth bond keeps the exposed metal at earth potential if a fault occurs."),
    (E_DC, "A DC generator converts", ["Mechanical energy into electrical energy", "Electrical energy into mechanical energy", "Heat directly into sound", "Light into a fuse rating"], "A", "The prime mover turns the generator. A DC motor does the opposite conversion."),
    (E_DC, "A DC motor converts", ["Electrical energy into mechanical energy", "Mechanical energy into electrical energy", "Alternating current into a higher frequency with no machine", "Insulation into copper"], "A", "Current in the armature, lying in a magnetic field, produces torque."),
    (E_DC, "A motor starter is used mainly to", ["Limit the heavy current at start", "Increase the start current as much as possible", "Remove the field forever", "Earth the shaft"], "A", "A stationary motor draws a large current. The starter inserts resistance or reduces voltage until the motor speeds up."),
    (E_DC, "The commutator of a DC machine", ["Reverses the connection of the armature coils at the right time", "Steps the voltage up like a transformer", "Measures insulation", "Is the cooling fan"], "A", "The commutator and brushes take or supply a unidirectional current at the terminals."),
    (E_MOT, "The induction motor most used in industry is the", ["Three-phase squirrel-cage motor", "Single-phase DC series motor only", "Stepper used as a ceiling fan", "Universal motor on every pump"], "A", "The rugged cage induction motor is the usual drive for pumps, fans and machines."),
    (E_MOT, "A DOL starter connects the motor", ["Straight to the full line voltage", "Through a star connection forever", "Only to a lamp", "Through a Megger"], "A", "Direct-on-line starting is used for small motors that can accept the starting current."),
    (E_MOT, "A star-delta starter first connects the windings in star in order to", ["Reduce the voltage per winding at start", "Increase the starting current", "Change the motor into a generator", "Remove two phases"], "A", "Star connection applies a lower voltage to each winding, then the starter changes over to delta for running."),
    (E_MOT, "A three-phase supply uses", ["Three alternating voltages displaced in phase", "One battery only", "Three direct currents of the same polarity", "A single lamp and a fuse"], "A", "The three phases are equally spaced in time, which gives a rotating field in the motor."),
    (E_INST, "An ammeter is connected in", ["Series with the load", "Parallel with the load", "Series with the earth only", "Place of the insulation"], "A", "The ammeter carries the load current, so it is inserted in series and has very low resistance."),
    (E_INST, "A voltmeter is connected in", ["Parallel with the points whose voltage is needed", "Series with the load", "Place of the fuse", "The stay wire"], "A", "The voltmeter has a high resistance and reads the potential difference across the two points."),
    (E_INST, "The voltage induced in a transformer winding increases if we increase the", ["Flux, frequency or number of turns", "Colour of the tank only", "Amount of steady direct current", "Length of the earth spike only"], "A", "Induced voltage depends on the turns, the frequency and the flux in the core."),
    (E_INST, "A current transformer is used so that an instrument can read", ["A large current through a small, safe current", "Insulation resistance", "Oil temperature only", "Pole height"], "A", "The current transformer scales the line current down for the ammeter or the relay."),
    (E_LAMP, "An LED lamp wastes less energy as heat than", ["An incandescent filament lamp", "A perfect mirror", "A fuse", "An earth electrode"], "A", "Most of the input to a filament lamp becomes heat. An LED turns a larger share into light."),
    (E_LAMP, "A semiconductor diode conducts", ["Mainly in one direction", "Equally well both ways like a resistor", "Only when it is an insulator", "Only alternating current of both polarities with no preference"], "A", "Forward bias lets current pass. Reverse bias blocks it, apart from a tiny leakage."),
    (E_LAMP, "A transistor is commonly used to", ["Amplify or switch a signal", "Replace the earth wire", "Measure sag", "Store water"], "A", "A small base current or voltage controls a larger collector current."),
    (E_LAMP, "A fluorescent lamp needs a choke or a driver because the discharge", ["Needs a controlled current", "Works on a dead short with no limit", "Uses no electricity", "Is a filament in vacuum only"], "A", "Once the gas conducts, its current must be limited, or the lamp would draw a destructive current."),
    (E_GEN, "A hydroelectric station obtains energy from", ["Falling water", "Only a diesel day-tank", "Only a solar cell on the dam", "The tide in every case"], "A", "Water from a height turns the turbine, which turns the generator. Idukki is a Kerala example."),
    (E_GEN, "A thermal station produces steam by burning", ["A fuel in the boiler", "Falling water alone", "Sunlight on a panel alone", "A storage battery alone"], "A", "The steam drives a turbine coupled to the alternator."),
    (E_GEN, "A nuclear station obtains heat from", ["Fission of nuclear fuel", "Burning of firewood", "A lead-acid cell", "A distribution fuse"], "A", "Controlled fission heats water or another coolant, and that heat raises steam."),
    (E_GEN, "A solar photovoltaic cell converts", ["Sunlight into electricity", "Coal into steam directly inside the cell", "Sound into current", "Wind into a transformer"], "A", "The cell produces a direct voltage when light falls on the semiconductor junction."),
    (E_TD, "Power is sent over long lines at high voltage so that the current, and the line loss, can be", ["Kept smaller", "Made as large as possible", "Removed by using direct current only in every Indian line", "Stored in the pole"], "A", "For a given power, a higher voltage means a smaller current, and heating loss depends on the square of the current."),
    (E_TD, "Alternating current is preferred for long-distance supply because a transformer can", ["Step the voltage up and down", "Change it into sound", "Store it in a battery with no conversion", "Remove the need for conductors"], "A", "Generation, transmission and use can each have a suitable voltage. Steady direct current cannot use a simple transformer."),
    (E_TD, "A distribution line differs from a transmission line because it", ["Feeds the consumers at the lower voltage", "Runs only inside the generator", "Carries no current", "Is always a telephone pair"], "A", "Transmission lines move bulk power. Distribution lines are the last stage out to the loads."),
    # --- Nurse ---
    (ANATOMY, "The human heart has", ["Four chambers", "Two chambers like a fish", "One chamber", "Six chambers"], "A", "Two atria receive blood and two ventricles pump it. The right side serves the lungs and the left side the body."),
    (ANATOMY, "The usual site for feeling the pulse at the wrist is the", ["Radial artery", "Femoral vein", "Carotid vein", "Aorta inside the abdomen"], "A", "The radial artery lies near the surface on the thumb side of the wrist."),
    (ANATOMY, "Insulin is produced by the", ["Pancreas", "Spleen", "Kidney", "Lung"], "A", "The islets of the pancreas release insulin, which lowers blood glucose."),
    (ANATOMY, "Bile is produced by the", ["Liver", "Stomach", "Pancreas", "Spleen"], "A", "The liver makes bile, which is stored in the gall bladder and helps digest fat."),
    (ANATOMY, "Exchange of oxygen and carbon dioxide in the lung takes place in the", ["Alveoli", "Bronchial cartilage only", "Pleura only", "Tracheal rings only"], "A", "The thin alveolar wall is where the gases pass between air and blood."),
    (ANATOMY, "The largest bone of the human body is the", ["Femur", "Stapes", "Clavicle", "Radius"], "A", "The femur, or thigh bone, is the longest and strongest bone. The stapes in the ear is the smallest."),
    (ANATOMY, "A normal resting adult pulse is most often", ["Between 60 and 100 beats in a minute", "Below 20 beats in a minute", "Above 180 beats in a minute", "Absent in a healthy person"], "A", "A resting pulse outside that range needs a clinical look, but athletes may sit a little lower."),
    (ANATOMY, "White blood cells are concerned mainly with", ["Defence against infection", "Clotting alone", "Carrying oxygen as their only job", "Producing bile"], "A", "The white cells take part in immunity. Red cells carry oxygen and platelets help clotting."),
    (NURSING, "Hand hygiene before patient contact is done to", ["Reduce the transfer of infection", "Warm the hands for comfort only", "Replace sterile gloves in surgery", "Measure the pulse"], "A", "Cleaning the hands is the single most useful everyday step against hospital infection."),
    (NURSING, "Vital signs commonly recorded by a nurse are", ["Temperature, pulse, respiration and blood pressure", "Height alone", "Only the name and address", "Only the diet preference"], "A", "These four observations show how the patient is at that moment."),
    (NURSING, "An intramuscular injection is given into", ["Muscle", "The skin surface only", "An artery on purpose", "The eye"], "A", "The drug is deposited in muscle, commonly the deltoid or the gluteal site, never into a vessel if that can be avoided."),
    (NURSING, "A sterile field is contaminated if the nurse", ["Turns her back on it or lets it get wet", "Keeps her hands above her waist", "Uses a sterile glove correctly", "Opens a sterile pack away from her clothing"], "A", "Moisture, an unsterile touch, or leaving the field unwatched breaks sterility."),
    (NURSING, "Florence Nightingale is remembered as the founder of", ["Modern nursing", "Radiology", "Dentistry", "Ayurvedic surgery"], "A", "Her work in the Crimea and at St Thomas's Hospital shaped trained nursing."),
    (NURSING, "Pressure sores are prevented mainly by", ["Regular change of position and care of the skin", "Keeping the patient on one side for days", "Withholding fluids", "Tight bandages over bony points"], "A", "Relieving pressure, keeping the skin clean and dry, and good nutrition protect the skin."),
    (NURSING, "Before giving a medicine the nurse confirms", ["The right patient, drug, dose, route and time", "Only the colour of the tablet", "Only the price", "The visitor's name"], "A", "These checks, with the right documentation, are the core of safe administration."),
    (NURSING, "A used needle is discarded in", ["A puncture-proof sharps container", "A paper waste basket", "The patient's locker", "The linen bag"], "A", "Sharps go straight into the designated container. They are not recapped with two hands."),
    (COMMUNITY, "Oral rehydration solution is used in", ["Diarrhoea, to replace water and salts", "A fracture of the femur", "An electric shock as the first act", "A foreign body in the ear"], "A", "ORS prevents dehydration. It does not replace the rest of the treatment when danger signs are present."),
    (COMMUNITY, "BCG vaccine is given to protect against", ["Tuberculosis", "Tetanus only", "Polio only", "Measles only"], "A", "BCG is the vaccine used against severe childhood tuberculosis."),
    (COMMUNITY, "The first aid for a small burn, after stopping the cause, is to", ["Cool the part with running water", "Apply ice directly for a long time", "Cover it with cotton wool that sticks", "Burst every blister"], "A", "Cooling with water limits the damage. Ice, butter and sticky cotton are avoided."),
    (COMMUNITY, "In adult basic life support by one rescuer, chest compressions and breaths are given in the ratio", ["30 compressions to 2 breaths", "5 compressions to 5 breaths", "1 compression to 10 breaths", "Compressions only after one hour"], "A", "Current basic life support uses 30 compressions and then 2 breaths, with the heels of the hands on the lower half of the sternum."),
    (COMMUNITY, "A primary health centre is meant to", ["Give essential care to a defined rural population", "Replace the medical college", "Perform only open-heart surgery", "Issue passports"], "A", "The PHC is the local unit for preventive and simple curative care, including maternal and child health."),
    (COMMUNITY, "Exclusive breastfeeding is advised for the first", ["Six months of life", "Two weeks only", "Two years with no other food ever after that", "One day"], "A", "Only breast milk is advised for about the first six months, after which other foods are added and breastfeeding continues."),
    (COMMUNITY, "DOTS is a strategy used in the control of", ["Tuberculosis", "A fracture", "Myopia", "Dental caries only"], "A", "Directly observed treatment helps the patient complete the anti-tuberculosis course."),
    # --- Fire, excise, police, forest, band ---
    (FIRE, "The three sides of the fire triangle are", ["Fuel, heat and oxygen", "Fuel, water and sand only", "Smoke, alarm and hose only", "Foam, powder and a bell"], "A", "Remove any one of fuel, heat or oxygen and the fire cannot continue."),
    (FIRE, "Water is a poor choice for a fire in", ["Live electrical equipment or burning oil", "Ordinary wood and paper", "Waste paper in a bin", "Cotton cloth"], "A", "Water conducts electricity and spreads burning oil. Those fires need the correct extinguisher."),
    (FIRE, "A flammable-liquid fire is best attacked, among common choices, with", ["Foam, carbon dioxide or dry powder", "A bucket of water thrown across the surface", "A fan that spreads the vapour", "Oily cotton"], "A", "Foam blankets the liquid. Water can float the burning liquid and spread it."),
    (FIRE, "The PASS method for an extinguisher is", ["Pull, aim, squeeze and sweep", "Push, alarm, stand and shout", "Pour, add, stir and store", "Point, abandon, shut and stop"], "A", "Pull the pin, aim at the base of the fire, squeeze the handle and sweep from side to side."),
    (FIRE, "The fire-service telephone number widely used in India is", ["101", "100", "108", "1098"], "A", "101 is the fire service. 100 has been the police number, 108 is ambulance, and 1098 is childline."),
    (FIRE, "Flash point of a liquid is the lowest temperature at which", ["Its vapour can ignite briefly", "The liquid boils", "The liquid freezes", "The container melts"], "A", "At the flash point the vapour flashes and goes out. The fire point is where burning continues."),
    (FIRE, "On finding a fire, the first useful public action is to", ["Raise the alarm and leave by a safe route", "Use the lift to go to the roof", "Hide the alarm", "Open every window and door to feed the fire"], "A", "Warning others and using the stairs, not the lift, comes before any attempt to fight a fire that is already large."),
    (FIRE, "A fire-hose nozzle is aimed at", ["The base of the flames", "The smoke at the ceiling only", "The people leaving", "The sky"], "A", "Water or foam at the base reaches the burning material. Playing on the smoke does not put the fire out."),
    (FIRE, "Kerala Fire and Rescue Services is the department that", ["Fights fire and carries out rescue", "Collects land tax", "Runs the excise shops", "Conducts the PSC written test"], "A", "The department handles fire calls, rescue and related safety work in the state."),
    (FIRE, "Smoke in a stairwell should be avoided by", ["Staying low and using a clearer route", "Standing upright in the thickest smoke", "Opening the door of a hot room with your face against it", "Going back for belongings"], "A", "Cleaner air is nearer the floor. A hot door is not opened into a developing fire."),
    (EXCISE, "The Kerala Abkari Act is the main state law on", ["Liquor and intoxicating drugs", "Forest timber", "School education", "Electricity supply"], "A", "Abkari law licences and controls liquor. Enforcement sits with the Excise department."),
    (EXCISE, "The NDPS Act deals with", ["Narcotic drugs and psychotropic substances", "Only income tax", "Only motor vehicles", "Only panchayat elections"], "A", "The Narcotic Drugs and Psychotropic Substances Act, 1985, is the central law on those substances."),
    (EXCISE, "Kerala State Beverages Corporation is concerned with", ["The wholesale and retail system for liquor run by the state", "Generating electricity", "Running fire stations", "Recruiting police constables"], "A", "BEVCO handles the state liquor trade. It is not a police or fire agency."),
    (EXCISE, "An excise duty is a tax on", ["Manufacture of specified goods", "Import across the customs frontier only", "A gift from a relative", "A salary"], "A", "Excise is charged on production. Customs duty is charged on import or export."),
    (EXCISE, "A licence under the Abkari law is required to", ["Sell liquor lawfully", "Teach in a school", "Drive a private car", "Open a bank account"], "A", "Sale and transport of liquor without the required licence is an offence under the Act."),
    (EXCISE, "Toddy is", ["A fermented drink from coconut or palm sap", "A brand of cement", "A forest pass", "A type of transformer"], "A", "Toddy shops, where permitted, work under excise control."),
    (BRANCH, "The special branch of the police is mainly", ["An intelligence wing", "The band wing", "The fire wing", "The hospital wing"], "A", "Special Branch collects and assesses intelligence for public order and security."),
    (BRANCH, "An FIR is the", ["First information report of a cognizable offence", "Final judgment of the court", "Fire inspection report", "Foreign investment return"], "A", "The first information sets the criminal law in motion for a cognizable case."),
    (BRANCH, "In a cognizable offence the police", ["May arrest without a warrant", "Cannot register any case", "Must wait for a civil suit", "Can act only after the sentence"], "A", "Cognizable offences are the more serious ones, in which the police can investigate and arrest without a warrant."),
    (BRANCH, "The Bharatiya Nyaya Sanhita, 2023, replaced the", ["Indian Penal Code", "Constitution", "Motor Vehicles Act", "Right to Information Act"], "A", "The Sanhita is the current criminal code. The old Penal Code was repealed when it came into force."),
    (BRANCH, "The Bharatiya Nagarik Suraksha Sanhita replaced the", ["Code of Criminal Procedure", "Civil Procedure Code", "Evidence Act of 1872 with no successor", "Indian Contract Act"], "A", "Procedure in criminal cases is now in the Suraksha Sanhita. The Evidence Act was replaced by the Bharatiya Sakshya Adhiniyam."),
    (BRANCH, "A person cannot be compelled to", ["Be a witness against himself", "Hold a driving licence if he drives", "Pay a lawful tax", "Appear when summoned in every case"], "A", "The protection against self-incrimination is a constitutional safeguard in criminal matters."),
    (FOREST, "The Wildlife Protection Act was enacted in", ["1972", "1950", "1947", "2005"], "A", "The Wildlife (Protection) Act, 1972, is the central law on wild animals, plants and protected areas."),
    (FOREST, "The state animal of Kerala is the", ["Nilgiri tahr", "Asiatic lion", "One-horned rhinoceros", "Snow leopard"], "A", "The Nilgiri tahr is the state animal. Eravikulam is its best-known home in Kerala."),
    (FOREST, "Periyar, in the Western Ghats of Kerala, is famous as a", ["Tiger reserve", "Desert national park", "Glacier park", "Coral island"], "A", "Periyar Tiger Reserve surrounds the Periyar lake near Thekkady."),
    (FOREST, "Silent Valley in Kerala is known for", ["Evergreen forest and its conservation battle", "Open desert", "A coalfield", "A tidal port"], "A", "The campaign to save Silent Valley stopped a hydroelectric project in the rain forest."),
    (FOREST, "Project Tiger was launched in", ["1973", "1947", "1991", "2014"], "A", "Project Tiger began in 1973 to protect the tiger and its habitat."),
    (FOREST, "The Western Ghats are recognised as a", ["Biodiversity hotspot", "Cold desert", "Coral atoll", "Inland salt lake"], "A", "The Ghats hold a very large number of plants and animals found nowhere else."),
    (FOREST, "The great Indian hornbill is the state", ["Bird of Kerala", "Animal of Kerala", "Tree of Kerala", "Flower of Kerala"], "A", "The hornbill is the state bird. The state flower is the kanikkonna and the state tree is the coconut palm."),
    (FOREST, "Social forestry mainly aims to", ["Grow trees on community and farm land outside the reserved forest", "Cut every mangrove", "Replace wildlife law", "Mine the Ghats"], "A", "Trees on roadsides, schools and farms supply fuel, fodder and shade and reduce pressure on natural forest."),
    (BAND, "The musical staff has", ["Five lines and four spaces", "Two lines", "Eight lines", "One line only in every case"], "A", "Notes are written on the five-line staff. The clef tells which line is which pitch."),
    (BAND, "A sharp placed before a note", ["Raises the pitch", "Lowers the pitch", "Silences the band", "Changes the instrument"], "A", "A sharp raises the note. A flat lowers it. A natural cancels either sign."),
    (BAND, "A flat placed before a note", ["Lowers the pitch", "Raises the pitch", "Doubles the speed", "Ends the piece"], "A", "The flat is the opposite of the sharp."),
    (BAND, "Tempo in music means the", ["Speed of the beat", "Loudness only", "Name of the composer", "Colour of the uniform"], "A", "Tempo is how fast the pulse goes. Dynamics is the loudness."),
    (BAND, "A traditional military bugle is a", ["Brass instrument used for calls", "String instrument", "Drum", "Keyboard"], "A", "Bugle calls give orders on parade. The side drum and bass drum mark the march."),
    (BAND, "The side drum in a police band is used to", ["Mark the rhythm of the march", "Play the melody of a violin", "Replace the bugle calls with chords", "Tune the singers"], "A", "The snare or side drum keeps the step. The bass drum marks the heavier beats."),
    (BAND, "Pitch of a note means how", ["High or low it sounds", "Long the concert is", "Many players stand", "Loud the hall is"], "A", "Pitch is the highness or lowness. Duration is how long the note is held."),
    # --- Engineering for Assistant Project Engineer ---
    (ENGMATH, "In a right-angled triangle the square on the hypotenuse equals", ["The sum of the squares on the other two sides", "The product of all three sides", "The difference of the two acute angles", "Half the base only"], "A", "This is Pythagoras' theorem, used constantly in layout and drawing."),
    (ENGMATH, "The area of a rectangle is", ["Length multiplied by breadth", "Length plus breadth", "Length divided by breadth", "Twice the length only"], "A", "Area is the product of the two sides. The perimeter is twice the sum of length and breadth."),
    (ENGMATH, "The sine of a thirty-degree angle equals", ["One half", "Zero", "One", "Two"], "A", "Sin 30° is 1/2. Sin 0° is 0 and sin 90° is 1."),
    (ENGMATH, "The ratio of the circumference of a circle to its width across the centre is", ["Pi", "Two", "One half", "Ten"], "A", "That ratio is pi, about 22/7 or 3.14, for every circle."),
    (ENGMATH, "The derivative of a constant is", ["Zero", "The constant itself", "One", "Infinity"], "A", "A constant does not change, so its rate of change is zero."),
    (DRAWING, "First-angle projection is the system", ["Commonly used in India", "Used only for maps of the sea", "In which the object is never drawn", "Reserved for artistic sketches"], "A", "Indian engineering drawings normally use first-angle projection. Third-angle is common in the United States."),
    (DRAWING, "An orthographic drawing shows the object by", ["Separate views such as front, top and side", "One pictorial view only", "A photograph", "A written specification with no views"], "A", "Each view is a true-shape look from one direction."),
    (DRAWING, "Concrete is made from cement together with", ["Sand and coarse aggregate", "Only water and paint", "Steel and no mineral", "Timber and glass"], "A", "Cement, fine aggregate, coarse aggregate and water make concrete. Steel is added when the member is reinforced."),
    (DRAWING, "A column in a building carries load mainly by", ["Compression", "Pure tension like a tie", "Bending like a beam only", "Torsion only"], "A", "A column is a compression member. A beam carries load by bending."),
    (DRAWING, "A drawing marked to a scale of one to one hundred means", ["The drawing is much smaller than the real object", "The drawing is larger than the object", "No measurement is possible", "The drawing is full size"], "A", "One unit on the paper stands for one hundred units on the job."),
    (DRAWING, "Contour lines on a map join points of", ["Equal elevation", "Equal temperature", "Equal rainfall", "Equal population"], "A", "A contour is a line of constant height. Close contours mean a steep slope."),
    (DRAWING, "Stress in a bar is", ["Force divided by the area that resists it", "Force multiplied by length", "Area divided by time", "Mass divided by volume, which is density"], "A", "Stress is the internal force per unit area. Strain is the change of length compared with the original length."),
    # --- A few more trade items so motor sets do not repeat the same six ---
    (ENGINE, "The cylinder head is bolted to the block in order to", ["Close the top of the cylinders", "Drive the wheels directly", "Store brake fluid", "Adjust the camber"], "A", "The head carries the valves or the injector and seals the combustion chamber."),
    (ENGINE, "Engine oil is checked with the", ["Dipstick", "Fuel gauge", "Tyre gauge", "Timing light only"], "A", "The dipstick shows the level in the sump. The engine should be on level ground."),
    (BRAKE, "Brake fade is the loss of braking when the", ["Friction surfaces overheat", "Tyres are new", "Tank is full", "Radio is on"], "A", "Hot linings lose friction. Cooling and the correct fluid reduce fade."),
    (BRAKE, "The handbrake usually works on the", ["Rear brakes through a cable or linkage", "Radiator cap", "Clutch pedal", "Fuel injector"], "A", "The parking brake is a mechanical system, separate from the hydraulic pedal circuit."),
    (STEER, "Power steering reduces the", ["Effort needed at the steering wheel", "Engine compression", "Brake-fluid level", "Gearbox ratios"], "A", "A hydraulic or electric assist helps the driver turn the wheels, especially when parking."),
    (STEER, "Ackermann steering lets the inner wheel", ["Turn through a sharper angle than the outer wheel", "Turn the opposite way", "Lock during a gentle bend", "Drive the engine"], "A", "The inner wheel follows a smaller circle, so it needs a larger steer angle."),
    (COOL, "A pressure cap on the radiator", ["Raises the boiling point of the coolant", "Stops the water pump", "Replaces the thermostat", "Adds oil to the sump"], "A", "Pressure in the closed system lets the coolant run hotter without boiling."),
    (COOL, "Oil in an engine reduces", ["Friction and also carries some heat away", "The octane number", "The need for pistons", "The battery voltage"], "A", "The oil film separates moving parts. The flow also picks up heat from the bearings and pistons."),
    (AUTO, "The horn circuit is protected by", ["A fuse", "The fuel injector", "The clutch plate", "The radiator cap"], "A", "A short in the horn wiring blows the fuse instead of burning the cable."),
    (AUTO, "The ignition switch in the start position feeds the", ["Starter solenoid", "Fuel tank", "Brake linings", "Wheel nuts"], "A", "The switch energises the solenoid, which then connects the battery to the starter motor."),
]


def _build():
    seen = set()
    items = []
    for topic, text, choices, answer, explanation in ROWS:
        key = " ".join(text.lower().split())
        if key in seen:
            raise ValueError(f"Duplicate stem: {text}")
        seen.add(key)
        if len(choices) != 4 or len(set(c.lower() for c in choices)) != 4:
            raise ValueError(f"Bad choices: {text}")
        items.append(_item(topic, text, list(choices), answer, explanation))
    return items


EXTRA_MCQS = _build()
