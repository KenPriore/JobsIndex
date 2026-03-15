#!/usr/bin/env python3
"""
Step 3 (Alternative): Score each occupation for AI exposure using heuristics.
Uses category, education level, pay, and keyword analysis of descriptions
to estimate AI exposure without an API key.
Reads data/occupations.csv, writes data/occupations_scored.csv
"""

import csv
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_CSV = DATA_DIR / "occupations.csv"
OUTPUT_CSV = DATA_DIR / "occupations_scored.csv"

# Category-based base scores (reflecting digital vs physical nature of work)
CATEGORY_BASE = {
    "Computer And Information Technology": 8,
    "Math": 8,
    "Media And Communication": 8,
    "Office And Administrative Support": 8,
    "Business And Financial": 7,
    "Legal": 7,
    "Arts And Design": 7,
    "Management": 6,
    "Life, Physical, And Social Science": 6,
    "Education, Training, And Library": 5,
    "Sales": 5,
    "Community And Social Service": 5,
    "Architecture And Engineering": 6,
    "Entertainment And Sports": 4,
    "Healthcare": 4,
    "Protective Service": 3,
    "Personal Care And Service": 2,
    "Food Preparation And Serving": 2,
    "Production": 3,
    "Installation, Maintenance, And Repair": 2,
    "Transportation And Material Moving": 2,
    "Farming, Fishing, And Forestry": 1,
    "Construction And Extraction": 1,
    "Building And Grounds Cleaning": 1,
    "Military": 3,
}

# Keywords that increase AI exposure score
HIGH_EXPOSURE_KEYWORDS = [
    (r'\b(software|programmer|coding|code|develop)\b', 2),
    (r'\b(data\s*(scientist|analyst|entry))\b', 2),
    (r'\b(writer|author|editor|copywriter)\b', 2),
    (r'\b(transcription|transcriptionist)\b', 3),
    (r'\b(bookkeep|accounting clerk|auditing clerk)\b', 2),
    (r'\b(paralegal|legal assistant)\b', 2),
    (r'\b(graphic design|web design|digital design)\b', 2),
    (r'\b(financial analyst|budget analyst|actuary)\b', 1),
    (r'\b(market research|survey research)\b', 1),
    (r'\b(clerk|clerical|receptionist|secretary|administrative assistant)\b', 1),
    (r'\b(customer service representative)\b', 1),
    (r'\b(translator|interpreter)\b', 1),
    (r'\b(insurance underwriter)\b', 2),
    (r'\b(desktop publish)\b', 2),
    (r'\b(teller)\b', 1),
    (r'\b(tax examiner|tax preparer)\b', 1),
    (r'\b(computer|information system|database|network architect)\b', 1),
    (r'\b(statistician|mathematician|operations research)\b', 1),
    (r'\b(technical writer)\b', 1),
    (r'\b(claims adjuster)\b', 1),
    (r'\b(compliance officer)\b', 1),
]

# Keywords that decrease AI exposure score
LOW_EXPOSURE_KEYWORDS = [
    (r'\b(construction|laborer|roofer|plumber|electrician|carpenter)\b', -2),
    (r'\b(janitor|clean|custodian|grounds|maintenance)\b', -2),
    (r'\b(nurse aide|nursing assistant|home health|personal care aide)\b', -1),
    (r'\b(firefighter|police|correctional officer|security guard)\b', -1),
    (r'\b(cook|chef|bartend|waiter|waitress|food prep)\b', -1),
    (r'\b(mechanic|technician|repair|installer)\b', -1),
    (r'\b(massage|barber|hairstylist|cosmetolog)\b', -2),
    (r'\b(childcare|child care|preschool)\b', -1),
    (r'\b(athlete|dancer|choreograph)\b', -2),
    (r'\b(surgeon|surgery|surgical|physical therap)\b', -1),
    (r'\b(welder|machinist|assembler|fabricat)\b', -1),
    (r'\b(driver|truck|bus driver|taxi)\b', -1),
    (r'\b(farmer|ranch|agricultural worker|logging|fishing)\b', -2),
    (r'\b(pest control|exterminator)\b', -2),
    (r'\b(veterinary assistant|animal care)\b', -1),
]

# Education-based adjustments
EDUCATION_ADJUSTMENT = {
    "No formal educational credential": -1,
    "High school diploma or equivalent": -0.5,
    "Some college, no degree": 0,
    "Postsecondary nondegree award": 0,
    "Associate's degree": 0,
    "Bachelor's degree": 1,
    "Master's degree": 0.5,
    "Doctoral or professional degree": 0,
}

# Specific occupation overrides (matching Karpathy's known scores)
OVERRIDES = {
    "Software Developers, Quality Assurance Analysts, and Testers": (9, "Primarily screen-based digital work producing code, tests, and documentation. AI coding assistants can already generate, review, and debug code at high quality, directly automating core tasks."),
    "Computer Programmers": (9, "Core work is writing code — one of the tasks most directly automatable by current AI models. AI can generate, debug, and optimize code across languages."),
    "Database Administrators and Architects": (8, "Database design, query optimization, and administration tasks are heavily digital. AI can generate SQL, optimize schemas, and automate routine DBA tasks."),
    "Data Scientists": (9, "Data analysis, model building, and insight generation are core AI capabilities. AI can write analysis code, build models, and generate reports."),
    "Mathematicians and Statisticians": (8, "Statistical analysis, mathematical modeling, and data interpretation are tasks AI excels at. Most work is purely digital."),
    "Financial Analysts": (8, "Financial modeling, report writing, and data analysis are heavily automatable. AI can process financial data and generate analysis much faster."),
    "Paralegals and Legal Assistants": (9, "Legal research, document review, contract analysis, and brief drafting are all tasks where AI is already highly capable."),
    "Writers and Authors": (8, "Content creation is a core AI capability. AI can draft articles, stories, marketing copy, and other written content at scale."),
    "Editors": (8, "Editing, proofreading, and content refinement are tasks AI handles well. The fully digital nature of the work increases exposure."),
    "Graphic Designers": (8, "AI image generation and design tools can create layouts, graphics, and visual content. Most work is screen-based digital output."),
    "Market Research Analysts": (8, "Data collection, survey analysis, trend identification, and report generation are all tasks AI can perform efficiently."),
    "Medical Transcriptionists": (10, "Fully digital output with no physical component. Speech-to-text AI already automates this task almost completely."),
    "Accountants and Auditors": (7, "Financial record-keeping, analysis, and reporting are heavily digital. AI can automate bookkeeping, detect anomalies, and generate reports."),
    "Web Developers and Digital Designers": (8, "Web development and digital design are tasks where AI coding and design tools are already highly capable."),
    "Computer and Information Research Scientists": (7, "While AI can assist with research, the creative and novel aspects of computer science research still require significant human insight."),
    "Information Security Analysts": (6, "AI can automate threat detection and response, but security requires contextual judgment, incident response, and adversarial thinking."),
    "Technical Writers": (8, "Documentation, manuals, and technical content creation are tasks AI can produce efficiently from source material."),
    "Actuaries": (8, "Risk modeling, statistical analysis, and report generation are heavily digital and mathematical — core AI strengths."),
    "Operations Research Analysts": (8, "Optimization, modeling, and quantitative analysis are tasks where AI excels."),
    "Bookkeeping, Accounting, and Auditing Clerks": (9, "Routine financial record-keeping and data entry are among the most automatable office tasks."),
    "Customer Service Representatives": (8, "AI chatbots and virtual assistants can handle most customer inquiries. Primarily digital communication work."),
    "Secretaries and Administrative Assistants": (8, "Scheduling, correspondence, data entry, and document management are all tasks AI can automate."),
    "General Office Clerks": (8, "Routine office tasks — filing, data entry, correspondence — are highly automatable by AI."),
    "Tellers": (8, "Routine financial transactions are already being automated by ATMs and digital banking. AI further reduces need."),
    "Registered Nurses": (4, "Nursing requires hands-on patient care, clinical judgment in person, and emotional support. AI can assist with documentation and monitoring but not core duties."),
    "Home Health and Personal Care Aides": (2, "Core work is physical — bathing, dressing, feeding, mobility assistance. Requires in-person presence and manual dexterity."),
    "Construction Laborers and Helpers": (1, "Physical labor in unpredictable outdoor environments. Manual material handling, site cleanup, and physical tasks resist automation."),
    "Janitors and Building Cleaners": (1, "Physical cleaning tasks in varied real-world environments. Requires navigating physical spaces and manual work."),
    "Roofers": (0, "Purely physical work at heights in outdoor environments. Zero digital output. Among the least automatable occupations."),
    "Electricians": (2, "Hands-on electrical installation and repair in physical environments. Requires manual dexterity and spatial reasoning."),
    "Plumbers, Pipefitters, and Steamfitters": (2, "Physical installation and repair work. Requires navigating building interiors and working with physical materials."),
    "Firefighters": (2, "Emergency response requiring physical presence, courage, and real-time decision-making in dangerous environments."),
    "Carpenters": (2, "Physical construction work requiring manual skills, spatial reasoning, and work in varied environments."),
    "Cooks": (3, "Physical food preparation with some recipe/menu planning that AI could assist with. Core work is manual."),
    "Bartenders": (2, "Physical drink preparation and social interaction. Requires in-person presence."),
    "Waiters and Waitresses": (3, "In-person food service with social interaction. Some ordering systems can be automated but core service is physical."),
    "Food and Beverage Serving and Related Workers": (3, "Physical serving tasks requiring in-person presence. Limited digital component."),
    "Dental Hygienists": (3, "Hands-on dental care requiring physical patient interaction and manual dexterity."),
    "Physicians and Surgeons": (5, "Mix of diagnosis (AI-assistable) and hands-on care/surgery (not automatable). AI aids documentation and diagnosis."),
    "Lawyers": (7, "Legal research, contract drafting, brief writing, and case analysis are all AI-assistable. Court appearances and client relations less so."),
    "Pharmacists": (6, "Drug dispensing is automatable, but patient counseling and clinical judgment provide some insulation."),
    "Cashiers": (7, "Self-checkout and automated payment systems are already replacing many cashier functions. Routine transaction processing."),
    "Retail Sales Workers": (4, "Mix of in-person customer interaction and routine tasks. E-commerce reduces need but in-store experience remains."),
    "Insurance Sales Agents": (6, "Policy comparison, quoting, and documentation are automatable. Relationship selling provides some protection."),
    "Real Estate Brokers and Sales Agents": (5, "Property showings require physical presence, but listing, marketing, and paperwork are automatable."),
    "Postsecondary Teachers": (5, "Teaching requires interpersonal engagement, but lecture prep, grading, and content creation are AI-assistable."),
    "High School Teachers": (5, "Classroom management and student interaction are physical. Lesson planning and grading can be AI-assisted."),
    "Kindergarten and Elementary School Teachers": (4, "Heavy emphasis on in-person care, socialization, and hands-on activities for young children."),
    "Preschool Teachers": (3, "Primarily physical care and socialization of young children. Minimal digital work component."),
    "Top Executives": (5, "Strategic decision-making, leadership, and stakeholder management. AI assists with analysis but judgment and relationships are key."),
    "Computer and Information Systems Managers": (6, "Management requires interpersonal skills, but technical planning and analysis components are AI-assistable."),
    "Financial Managers": (6, "Financial analysis and reporting are automatable, but team management and strategic decisions less so."),
    "Advertising, Promotions, and Marketing Managers": (7, "Campaign strategy, content creation, and analytics are heavily AI-assistable. Creative direction and client management less so."),
    "Human Resources Specialists": (7, "Resume screening, policy documentation, and benefits administration are all AI-automatable tasks."),
    "Human Resources Managers": (6, "People management and culture building resist automation, but HR processes and analytics are AI-assistable."),
    "Training and Development Specialists": (6, "Content creation and training design are AI-assistable, but in-person facilitation and coaching are not."),
    "Public Relations Specialists": (7, "Writing press releases, media monitoring, and content creation are core AI capabilities."),
    "Photographers": (5, "Physical presence required for shoots, but post-processing and AI-generated imagery increase competitive pressure."),
    "Massage Therapists": (1, "Purely hands-on physical therapy requiring human touch and manual dexterity."),
    "Security Guards and Gambling Surveillance Officers": (3, "Physical presence and surveillance. AI can assist with monitoring but guards provide physical deterrence."),
    "Police and Detectives": (3, "Physical enforcement, investigations, and community interaction. AI aids analysis but core work is in-person."),
    "Bus Drivers": (3, "Physical operation of vehicles. Autonomous driving technology is advancing but not yet replacing most bus routes."),
    "Heavy and Tractor-trailer Truck Drivers": (4, "Autonomous driving technology poses medium-term threat, but current work is physical operation."),
    "Delivery Truck Drivers and Driver/Sales Workers": (3, "Physical driving and delivery requiring navigation of real-world environments."),
    "Hand Laborers and Material Movers": (2, "Physical movement of materials. Requires manual labor in real-world environments."),
    "Taxi Drivers, Shuttle Drivers, and Chauffeurs": (4, "Autonomous vehicle technology poses threat, but current work is physical driving."),
    "Medical Assistants": (4, "Mix of administrative tasks (AI-assistable) and hands-on clinical support."),
    "Nursing Assistants and Orderlies": (2, "Physical patient care — bathing, feeding, mobility. Requires in-person presence."),
    "EMTs and Paramedics": (2, "Emergency medical response requiring physical presence and hands-on care in unpredictable environments."),
    "Dental Assistants": (3, "Hands-on dental support work with some administrative tasks."),
    "Pharmacy Technicians": (5, "Mix of physical dispensing and digital record-keeping. Automated dispensing systems increase exposure."),
    "Physical Therapists": (3, "Hands-on therapeutic exercises and patient interaction. Treatment planning can be AI-assisted."),
    "Occupational Therapists": (3, "Hands-on therapy requiring patient interaction and physical activity modification."),
    "Speech-Language Pathologists": (4, "In-person therapy sessions with some assessment and documentation that AI can assist."),
    "Veterinarians": (4, "Hands-on animal care and surgery. Diagnosis can be AI-assisted but treatment is physical."),
    "Diagnostic Medical Sonographers": (4, "Hands-on imaging requiring patient positioning, but AI can assist with image interpretation."),
    "Radiologic and MRI Technologists": (4, "Equipment operation requires physical presence, but image analysis is AI-assistable."),
    "Clinical Laboratory Technologists and Technicians": (5, "Lab analysis and testing. Automation and AI can handle routine analyses."),
    "Dentists": (4, "Hands-on dental procedures. Diagnosis and treatment planning can be AI-assisted."),
    "Chiropractors": (3, "Hands-on physical treatment requiring manual manipulation."),
    "Optometrists": (4, "Eye exams have physical component but diagnostic analysis is AI-assistable."),
    "Coaches and Scouts": (3, "In-person coaching and physical activity. Game analysis can be AI-assisted."),
    "Athletes and Sports Competitors": (1, "Physical performance is the core product. Cannot be automated."),
    "Actors": (3, "Physical performance and emotional expression. AI-generated content is emerging but live performance persists."),
    "Producers and Directors": (5, "Creative vision and project management. AI can assist with editing, effects, and content generation."),
    "Announcers and DJs": (6, "Voice work and content curation. AI can generate voice content and curate playlists."),
    "Interpreters and Translators": (8, "Real-time translation is a core AI capability. Written translation is nearly fully automatable."),
    "News Analysts, Reporters, and Journalists": (7, "News writing, research, and analysis are AI-assistable. Investigative work and source relationships less so."),
    "Claims Adjusters, Appraisers, Examiners, and Investigators": (7, "Claims processing, documentation review, and damage assessment are increasingly automated."),
    "Compliance Officers": (7, "Regulatory monitoring, policy review, and compliance documentation are AI-assistable tasks."),
    "Management Analysts": (7, "Business analysis, report writing, and process optimization are core AI strengths."),
    "Project Management Specialists": (6, "Project planning and tracking are automatable, but team coordination and stakeholder management are not."),
    "Logisticians": (7, "Supply chain optimization, routing, and inventory management are tasks where AI excels."),
    "Cost Estimators": (7, "Estimation based on data analysis and historical patterns — tasks AI handles well."),
    "Personal Financial Advisors": (6, "Portfolio analysis and financial planning are AI-assistable, but client relationships provide protection."),
    "Loan Officers": (7, "Credit analysis and loan processing are increasingly automated."),
    "Credit Counselors": (5, "Mix of financial analysis (automatable) and personal counseling (not automatable)."),
    "Budget Analysts": (8, "Budget analysis, forecasting, and report generation are highly automatable digital tasks."),
    "Purchasing Managers, Buyers, and Purchasing Agents": (6, "Procurement analysis and vendor comparison are automatable, but relationship management is not."),
    "Property Appraisers and Assessors": (6, "Property valuation uses data analysis (AI-assistable) and physical inspection (not automatable)."),
    "Social Workers": (4, "Client interaction, advocacy, and crisis intervention require human judgment and empathy."),
    "Substance Abuse, Behavioral Disorder, and Mental Health Counselors": (4, "Therapeutic relationships require human connection. Documentation and assessment can be AI-assisted."),
    "Psychologists": (5, "Therapy sessions require human interaction, but assessment, research, and report writing are AI-assistable."),
    "School and Career Counselors and Advisors": (5, "In-person counseling with students. Information provision and scheduling are automatable."),
    "Marriage and Family Therapists": (4, "Therapeutic relationships require human presence and emotional intelligence."),
    "Rehabilitation Counselors": (4, "Client interaction and advocacy require human presence."),
    "Probation Officers and Correctional Treatment Specialists": (4, "Supervision requires physical presence. Risk assessment and documentation are AI-assistable."),
    "Social and Human Service Assistants": (4, "Client interaction and service coordination. Some administrative tasks are automatable."),
    "Community Health Workers": (3, "Community outreach and health education require physical presence and cultural competency."),
    "Health Education Specialists": (5, "Content creation and program design are AI-assistable, but community engagement is not."),
    "Farmers, Ranchers, and Other Agricultural Managers": (3, "Physical farm work and management. AI aids crop planning and monitoring but not physical labor."),
    "Agricultural Workers": (1, "Physical planting, harvesting, and manual farm labor in outdoor environments."),
    "Logging Workers": (1, "Physical cutting and moving of timber in forests. Highly physical outdoor work."),
    "Fishing and Hunting Workers": (1, "Physical work in natural environments."),
    "Forest and Conservation Workers": (2, "Physical conservation work outdoors."),
    "Animal Care and Service Workers": (2, "Physical care of animals requiring handling and feeding."),
    "Correctional Officers and Bailiffs": (3, "Physical security and inmate management. Requires in-person presence."),
    "Private Detectives and Investigators": (5, "Physical surveillance combined with digital research and analysis."),
    "Fire Inspectors": (5, "Physical site inspections combined with code compliance documentation."),
    "Air Traffic Controllers": (5, "Real-time coordination requiring intense focus. AI can assist but human oversight critical for safety."),
    "Airline and Commercial Pilots": (4, "Physical operation of aircraft. Automation handles much cruise flight but takeoff/landing and emergencies need humans."),
    "Flight Attendants": (2, "In-person safety and service aboard aircraft. Requires physical presence."),
    "Railroad Workers": (3, "Physical operation and maintenance of railroad equipment."),
    "Water Transportation Workers": (3, "Physical operation of watercraft."),
    "Material Moving Machine Operators": (3, "Physical operation of machinery. Automation advancing but not yet widespread."),
    "Childcare Workers": (2, "Physical care and supervision of children. Requires in-person presence and attention."),
    "Barbers, Hairstylists, and Cosmetologists": (1, "Hands-on personal grooming services. Requires manual dexterity and client interaction."),
    "Fitness Trainers and Instructors": (3, "Physical demonstration and in-person motivation. Online content creation is AI-assistable."),
    "Funeral Service Workers": (3, "In-person service combining physical preparation and emotional support."),
    "Recreation Workers": (2, "Physical activity coordination and supervision. Requires in-person presence."),
    "Tour and Travel Guides": (4, "In-person guiding with knowledge sharing. AI travel planning is a growing substitute."),
    "Concierges": (5, "Information provision is automatable, but personal service and local expertise provide some protection."),
    "Skincare Specialists": (2, "Hands-on skincare treatments. Requires physical presence and manual technique."),
    "Manicurists and Pedicurists": (1, "Hands-on nail care requiring manual dexterity."),
    "Gambling Services Workers": (4, "Mix of physical dealing and game management. Some automation possible."),
    "Desktop Publishers": (9, "Digital layout and document formatting — tasks AI design tools can handle."),
    "Bill and Account Collectors": (7, "Communication-based work with script-following. AI can automate outreach and payment processing."),
    "Information Clerks": (7, "Information provision and data entry — core AI capabilities."),
    "Material Recording Clerks": (6, "Inventory tracking and record-keeping. Automation and AI increasingly handle these tasks."),
    "Financial Clerks": (7, "Routine financial processing and record-keeping."),
    "Postal Service Workers": (4, "Physical mail sorting and delivery. Some sorting is automated but delivery requires physical presence."),
    "Public Safety Telecommunicators": (5, "Emergency call handling requires human judgment, but AI can assist with call routing and information."),
    "Advertising Sales Agents": (6, "Sales outreach and campaign planning are partially automatable. Relationship selling is not."),
    "Securities, Commodities, and Financial Services Sales Agents": (6, "Trading and financial product sales. Algorithmic trading reduces need, but client relationships persist."),
    "Wholesale and Manufacturing Sales Representatives": (5, "Product knowledge and relationship selling. AI assists with prospecting and data analysis."),
    "Travel Agents": (7, "Trip planning and booking are heavily automatable by AI and online platforms."),
    "Sales Engineers": (5, "Technical sales requiring product demonstrations. Technical knowledge delivery is AI-assistable."),
    "Models": (5, "Physical appearance is the product, but AI-generated imagery is an emerging competitive threat."),
    "Assemblers and Fabricators": (3, "Physical assembly work. Automation advancing in manufacturing but many tasks still manual."),
    "Bakers": (2, "Physical food preparation requiring manual skills."),
    "Butchers": (2, "Physical meat processing."),
    "Food Processing Equipment Workers": (3, "Machine operation in food production. Increasing automation."),
    "Machinists and Tool and Die Makers": (3, "Skilled physical work with machines. CNC programming can be AI-assisted."),
    "Metal and Plastic Machine Workers": (3, "Physical machine operation."),
    "Welders, Cutters, Solderers, and Brazers": (2, "Skilled physical joining work. Robotic welding exists but many applications need manual skill."),
    "Woodworkers": (2, "Physical craftsmanship with wood. CNC assists but custom work is manual."),
    "Quality Control Inspectors": (5, "Visual inspection and testing. AI computer vision can automate many inspections."),
    "Power Plant Operators, Distributors, and Dispatchers": (5, "System monitoring and operation. AI can optimize but operators needed for safety."),
    "Semiconductor Processing Technicians": (4, "Physical equipment operation in cleanrooms with some process monitoring."),
    "Stationary Engineers and Boiler Operators": (4, "Equipment monitoring and maintenance."),
    "Water and Wastewater Treatment Plant and System Operators": (4, "Plant operation with physical and digital monitoring components."),
    "Painting and Coating Workers": (2, "Physical surface preparation and painting."),
    "Jewelers and Precious Stone and Metal Workers": (3, "Skilled handcraft. CAD design is AI-assistable but physical crafting is not."),
    "Dental and Ophthalmic Laboratory Technicians and Medical Appliance Technicians": (4, "Physical fabrication of dental/optical devices. CAD/CAM is AI-assistable."),
    "Architects": (7, "Design, planning, and documentation are heavily digital. AI can generate designs and documentation."),
    "Civil Engineers": (6, "Engineering analysis and design are AI-assistable, but site work and inspections are physical."),
    "Mechanical Engineers": (6, "Design and analysis are digital tasks. AI can assist with CAD, simulation, and optimization."),
    "Electrical and Electronics Engineers": (6, "Circuit design and analysis are AI-assistable. Some physical testing required."),
    "Chemical Engineers": (6, "Process design and optimization are AI-assistable. Lab work is physical."),
    "Industrial Engineers": (7, "Process optimization, efficiency analysis, and workflow design are core AI strengths."),
    "Bioengineers and Biomedical Engineers": (6, "Research and design with some physical lab/clinical components."),
    "Environmental Engineers": (6, "Environmental analysis and compliance documentation are AI-assistable. Field work is physical."),
    "Aerospace Engineers": (6, "Design and simulation are digital. Physical testing and manufacturing oversight less automatable."),
    "Computer Hardware Engineers": (6, "Hardware design is digital but prototyping and testing have physical components."),
    "Nuclear Engineers": (6, "Analysis and design are digital. Plant operations require physical presence."),
    "Materials Engineers": (6, "Research and analysis with lab work components."),
    "Petroleum Engineers": (6, "Subsurface analysis is digital but field work is physical."),
    "Marine Engineers and Naval Architects": (6, "Ship design is digital. Sea trials and inspections are physical."),
    "Surveying and Mapping Technicians": (4, "Field measurements are physical. Data processing is AI-assistable."),
    "Surveyors": (4, "Physical field work with digital data processing."),
    "Landscape Architects": (6, "Design is digital. Site assessment requires physical visits."),
    "Drafters": (8, "Technical drawing and CAD work is heavily digital and AI-assistable."),
    "Art Directors": (7, "Creative direction with heavy digital design component."),
    "Fashion Designers": (7, "Design ideation and sketching are AI-assistable. Physical fitting is not."),
    "Industrial Designers": (7, "Product design using CAD — AI-assistable digital work."),
    "Interior Designers": (6, "Space planning and visualization are digital. Site visits and client meetings are physical."),
    "Special Effects Artists and Animators": (7, "Digital content creation — core AI capability for generation and enhancement."),
    "Set and Exhibit Designers": (5, "Design is digital but physical construction and installation are not."),
    "Craft and Fine Artists": (4, "Physical creation of art. AI-generated art is competitive but handmade work retains value."),
    "Floral Designers": (2, "Physical arrangement of flowers. Minimal digital component."),
    "Grounds Maintenance Workers": (1, "Physical outdoor maintenance work."),
    "Pest Control Workers": (1, "Physical pest treatment in real-world environments."),
    "Automotive Service Technicians and Mechanics": (3, "Physical vehicle repair. Diagnostic tools are increasingly digital."),
    "Diesel Service Technicians and Mechanics": (3, "Physical repair of heavy vehicles."),
    "Automotive Body and Glass Repairers": (2, "Physical repair work."),
    "HVAC Mechanics": (3, "Physical installation and repair."),
    "General Maintenance and Repair Workers": (2, "General physical repair and maintenance tasks."),
    "Heating, Air Conditioning, and Refrigeration Mechanics and Installers": (3, "Physical HVAC work."),
    "Heavy Vehicle and Mobile Equipment Service Technicians": (2, "Physical repair of heavy equipment."),
    "Industrial Machinery Mechanics, Machinery Maintenance Workers, and Millwrights": (3, "Physical machinery repair and maintenance."),
    "Aircraft and Avionics Equipment Mechanics and Technicians": (3, "Physical aircraft repair with digital diagnostic components."),
    "Electrical and Electronics Installers and Repairers": (3, "Physical installation and repair."),
    "Medical Equipment Repairers": (3, "Physical repair of medical devices."),
    "Telecommunications Technicians": (3, "Physical installation with digital configuration."),
    "Wind Turbine Technicians": (2, "Physical maintenance at height."),
    "Electrical Power-Line Installers and Repairers": (2, "Physical installation at height."),
    "Small Engine Mechanics": (2, "Physical repair work."),
    "Calibration Technologists and Technicians": (4, "Precision instrument calibration with digital and physical components."),
    "Arbitrators, Mediators, and Conciliators": (5, "Dispute resolution requiring interpersonal skills. Case analysis is AI-assistable."),
    "Judges and Hearing Officers": (5, "Legal judgment requiring human authority. Case research is AI-assistable."),
    "Court Reporters and Simultaneous Captioners": (9, "Real-time transcription — directly automatable by speech-to-text AI."),
    "Boilermakers": (2, "Physical fabrication and repair of boilers."),
    "Construction and Building Inspectors": (4, "Physical site inspections with digital reporting."),
    "Construction Equipment Operators": (2, "Physical operation of heavy machinery."),
    "Drywall Installers, Ceiling Tile Installers, and Tapers": (1, "Physical installation work."),
    "Elevator and Escalator Installers and Repairers": (2, "Physical installation and repair."),
    "Glaziers": (1, "Physical glass installation."),
    "Hazardous Materials Removal Workers": (1, "Physical hazmat cleanup in dangerous environments."),
    "Insulation Workers": (1, "Physical insulation installation."),
    "Oil and Gas Workers": (2, "Physical extraction work."),
    "Painters, Construction and Maintenance": (1, "Physical painting work."),
    "Sheet Metal Workers": (2, "Physical metalwork."),
    "Solar Photovoltaic Installers": (2, "Physical installation of solar panels."),
    "Ironworkers": (2, "Physical structural iron work at height."),
    "Flooring Installers and Tile and Stone Setters": (1, "Physical flooring installation."),
    "Masonry Workers": (1, "Physical brickwork and stonework."),
    "Adult Basic and Secondary Education and ESL Teachers": (5, "Teaching with AI-assistable content creation and assessment."),
    "Career and Technical Education Teachers": (4, "Hands-on skill instruction. Lecture content is AI-assistable."),
    "Middle School Teachers": (5, "Classroom teaching with AI-assistable planning and grading."),
    "Special Education Teachers": (4, "Individualized instruction requiring close personal interaction."),
    "Teacher Assistants": (4, "Classroom support with some administrative tasks."),
    "Tutors": (6, "One-on-one instruction. AI tutoring systems are a growing alternative."),
    "Instructional Coordinators": (6, "Curriculum development and training — tasks AI can assist with significantly."),
    "Librarians and Library Media Specialists": (6, "Information services and cataloging are AI-assistable. Community engagement less so."),
    "Library Technicians and Assistants": (5, "Collection management and patron services. Routine tasks are automatable."),
    "Archivists, Curators, and Museum Workers": (5, "Digital cataloging is automatable, but physical preservation and exhibition design are not."),
    "Music Directors and Composers": (6, "AI can generate music and arrangements. Creative vision and live performance less automatable."),
    "Musicians and Singers": (3, "Live performance is physical. Recording and composition face AI competition."),
    "Dancers and Choreographers": (2, "Physical performance art."),
    "Umpires, Referees, and Other Sports Officials": (3, "Physical presence required. AI assists with replay review."),
    "Chefs and Head Cooks": (3, "Physical cooking with menu planning that AI can assist."),
    "Food Preparation Workers": (2, "Physical food prep work."),
    "Athletic Trainers": (3, "Physical assessment and treatment of athletes."),
    "Audiologists": (4, "Clinical assessment with digital diagnostic tools."),
    "Cardiovascular Technologists and Technicians": (4, "Equipment operation with physical patient interaction."),
    "Dietitians and Nutritionists": (5, "Nutrition planning is AI-assistable. Patient counseling requires personal interaction."),
    "Exercise Physiologists": (4, "Physical assessment and exercise prescription."),
    "Genetic Counselors": (5, "Genetic data interpretation (AI-assistable) combined with patient counseling."),
    "Health Information Technologists and Medical Registrars": (7, "Digital health records management and coding — tasks AI handles well."),
    "Licensed Practical and Licensed Vocational Nurses": (3, "Hands-on nursing care requiring physical patient interaction."),
    "Medical Dosimetrists": (6, "Radiation dose calculations and treatment planning — computational tasks."),
    "Medical Records Specialists": (8, "Digital record management and coding — highly automatable."),
    "Nuclear Medicine Technologists": (4, "Equipment operation with physical patient positioning."),
    "Nurse Anesthetists, Nurse Midwives, and Nurse Practitioners": (4, "Advanced practice requiring hands-on patient care."),
    "Occupational Health and Safety Specialists and Technicians": (5, "Site inspections (physical) with compliance documentation (digital)."),
    "Occupational Therapy Assistants and Aides": (3, "Physical therapy assistance."),
    "Opticians": (4, "Eyewear fitting (physical) with measurements and ordering (digital)."),
    "Orthotists and Prosthetists": (4, "Custom device fabrication and fitting — physical work with digital design."),
    "Phlebotomists": (2, "Physical blood collection."),
    "Physical Therapist Assistants and Aides": (3, "Physical therapy support."),
    "Physician Assistants": (4, "Clinical care requiring patient examination. Documentation is AI-assistable."),
    "Podiatrists": (4, "Foot/ankle care requiring physical examination and treatment."),
    "Psychiatric Technicians and Aides": (3, "Patient care and monitoring requiring physical presence."),
    "Radiation Therapists": (4, "Equipment operation with patient positioning."),
    "Recreational Therapists": (3, "Activity-based therapy requiring personal interaction."),
    "Respiratory Therapists": (3, "Equipment operation and patient care."),
    "Surgical Assistants and Technologists": (3, "Operating room support requiring physical presence."),
    "Veterinary Assistants and Laboratory Animal Caretakers": (2, "Physical animal handling and care."),
    "Veterinary Technologists and Technicians": (3, "Animal care with some lab work."),
    "Administrative Services and Facilities Managers": (6, "Facility management with administrative oversight."),
    "Architectural and Engineering Managers": (6, "Technical project oversight. Analysis and planning are AI-assistable."),
    "Compensation and Benefits Managers": (7, "Compensation analysis and program design — digital analytical work."),
    "Construction Managers": (4, "Physical site oversight with project planning (AI-assistable)."),
    "Elementary, Middle, and High School Principals": (5, "School management with administrative tasks (AI-assistable) and personal leadership."),
    "Emergency Management Directors": (5, "Crisis planning (AI-assistable) with emergency coordination (physical)."),
    "Entertainment and Recreation Managers": (5, "Facility management with creative programming."),
    "Food Service Managers": (4, "Physical restaurant oversight with administrative tasks."),
    "Industrial Production Managers": (5, "Production oversight with optimization (AI-assistable)."),
    "Lodging Managers": (5, "Hospitality management with guest relations (physical) and operations (AI-assistable)."),
    "Medical and Health Services Managers": (5, "Healthcare administration with clinical oversight."),
    "Natural Sciences Managers": (6, "Research program management with analytical components."),
    "Postsecondary Education Administrators": (6, "Administrative oversight with data analysis."),
    "Preschool and Childcare Center Directors": (4, "Childcare management requiring physical presence."),
    "Property, Real Estate, and Community Association Managers": (5, "Property management with administrative and physical components."),
    "Public Relations and Fundraising Managers": (7, "Communications strategy and content creation — AI-assistable."),
    "Sales Managers": (6, "Sales strategy and team management."),
    "Social and Community Service Managers": (5, "Program management with community engagement."),
    "Training and Development Managers": (6, "Program design (AI-assistable) with leadership."),
    "Transportation, Storage, and Distribution Managers": (5, "Logistics optimization (AI-assistable) with operational oversight."),
    "Compensation, Benefits, and Job Analysis Specialists": (7, "Data analysis and policy documentation — digital work."),
    "Financial Examiners": (7, "Financial review and compliance analysis — digital analytical work."),
    "Fundraisers": (5, "Relationship building with campaign management (AI-assistable)."),
    "Insurance Underwriters": (8, "Risk assessment and policy evaluation — highly automatable analytical work."),
    "Labor Relations Specialists": (5, "Negotiation and interpersonal work with policy analysis."),
    "Meeting, Convention, and Event Planners": (5, "Event logistics with vendor coordination (physical) and planning (AI-assistable)."),
    "Tax Examiners and Collectors, and Revenue Agents": (7, "Tax analysis and compliance — digital analytical work."),
    "Computer Network Architects": (7, "Network design and planning — digital work. Implementation has physical components."),
    "Computer Support Specialists": (6, "Troubleshooting (AI-assistable) with some physical hardware support."),
    "Computer Systems Analysts": (8, "System analysis, requirements gathering, and documentation — digital work."),
    "Network and Computer Systems Administrators": (7, "System management — increasingly automated with AI ops tools."),
    "Broadcast, Sound, and Video Technicians": (4, "Physical equipment operation with digital editing."),
    "Film and Video Editors and Camera Operators": (6, "Physical camera work + digital editing (AI-assistable)."),
    "Epidemiologists": (6, "Data analysis and disease modeling — AI-assistable."),
    "Forensic Science Technicians": (4, "Physical evidence collection with digital analysis."),
    "Medical Scientists": (5, "Research combining lab work (physical) with data analysis (AI-assistable)."),
    "Biochemists and Biophysicists": (5, "Lab research with computational analysis."),
    "Biological Technicians": (4, "Lab work with physical sample handling."),
    "Chemical Technicians": (4, "Lab work with physical testing."),
    "Chemists and Materials Scientists": (5, "Lab research with computational analysis."),
    "Conservation Scientists and Foresters": (3, "Fieldwork with resource management."),
    "Economists": (7, "Economic modeling and analysis — core AI strengths."),
    "Environmental Science and Protection Technicians": (4, "Field sampling with lab analysis."),
    "Environmental Scientists and Specialists": (5, "Environmental analysis with fieldwork."),
    "Geoscientists": (5, "Geological analysis with fieldwork."),
    "Historians": (6, "Research and writing — AI-assistable."),
    "Hydrologists": (5, "Water resource analysis with fieldwork."),
    "Microbiologists": (5, "Lab research with digital analysis."),
    "Nuclear Technicians": (4, "Physical equipment operation with monitoring."),
    "Physicists and Astronomers": (5, "Research combining computation (AI-assistable) with experimental work."),
    "Political Scientists": (7, "Research, analysis, and writing — AI-assistable."),
    "Sociologists": (6, "Research and analysis with fieldwork."),
    "Urban and Regional Planners": (6, "Planning and analysis with community engagement."),
    "Zoologists and Wildlife Biologists": (4, "Fieldwork with data analysis."),
    "Agricultural and Food Science Technicians": (4, "Lab and field work."),
    "Agricultural and Food Scientists": (5, "Research with lab work."),
    "Anthropologists and Archeologists": (4, "Fieldwork with research analysis."),
    "Atmospheric Scientists, Including Meteorologists": (6, "Weather modeling and analysis — computational work AI can assist."),
    "Geological and Hydrologic Technicians": (4, "Field sampling with analysis."),
    "Geographers": (6, "Spatial analysis and mapping — digital work."),
    "Survey Researchers": (7, "Survey design, data collection, and analysis — AI-assistable."),
    "Aerospace Engineering and Operations Technologists and Technicians": (5, "Technical support with testing and analysis."),
    "Civil Engineering Technologists and Technicians": (5, "Technical support with field and office work."),
    "Electrical and Electronic Engineering Technologists and Technicians": (5, "Technical testing and support."),
    "Electro-mechanical and Mechatronics Technologists and Technicians": (4, "Physical system assembly and testing."),
    "Environmental Engineering Technologists and Technicians": (5, "Environmental testing and monitoring."),
    "Health and Safety Engineers": (6, "Safety analysis and compliance — digital analytical work with site visits."),
    "Industrial Engineering Technologists and Technicians": (5, "Process analysis with some physical work."),
    "Mechanical Engineering Technologists and Technicians": (5, "Technical support with testing."),
    "Mining and Geological Engineers": (5, "Mining design with field work."),
    "Cartographers and Photogrammetrists": (7, "Map creation and spatial analysis — digital work AI can assist."),
}


def score_occupation(record):
    """Score an occupation using heuristics."""
    name = record["occupation"]
    category = record["category"]
    education = record.get("education", "")
    description = record.get("description", "")
    pay = int(record["median_pay"]) if record.get("median_pay") else None

    # Check overrides first
    if name in OVERRIDES:
        return OVERRIDES[name]

    # Start with category base score
    base = CATEGORY_BASE.get(category, 4)

    # Apply keyword adjustments
    text = f"{name} {description}".lower()
    adjustment = 0

    for pattern, delta in HIGH_EXPOSURE_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            adjustment += delta

    for pattern, delta in LOW_EXPOSURE_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            adjustment += delta  # delta is negative

    # Education adjustment
    edu_adj = EDUCATION_ADJUSTMENT.get(education, 0)

    # Compute final score (clamp 0-10)
    score = max(0, min(10, round(base + adjustment + edu_adj)))

    # Generate reasoning
    if score >= 8:
        reasoning = f"Primarily digital/knowledge work. Most core tasks can be augmented or automated by AI. Category: {category}."
    elif score >= 6:
        reasoning = f"Significant digital work component with some physical/interpersonal elements that resist automation. Category: {category}."
    elif score >= 4:
        reasoning = f"Mixed physical and digital task profile. AI can assist with some tasks but core duties have physical or interpersonal components. Category: {category}."
    elif score >= 2:
        reasoning = f"Primarily physical or hands-on work with limited digital component. Most core duties require in-person presence. Category: {category}."
    else:
        reasoning = f"Almost entirely physical work in real-world environments. Minimal digital output. Category: {category}."

    return score, reasoning


def main():
    if not INPUT_CSV.exists():
        print(f"Input file not found: {INPUT_CSV}")
        print("Run 02_extract_data.py first.")
        return

    # Read input CSV
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        records = list(reader)

    # Filter non-occupation pages
    records = [r for r in records if r["occupation"] not in ("Glossary", "OOH FAQs", "Teacher's Guide", "Military Careers")]

    print(f"Scoring {len(records)} occupations with heuristics...")

    fieldnames = [
        "occupation", "category", "median_pay", "num_jobs", "outlook_pct",
        "education", "work_experience", "training", "description", "url",
        "ai_score", "ai_reasoning"
    ]

    results = []
    for record in records:
        score, reasoning = score_occupation(record)
        record["ai_score"] = score
        record["ai_reasoning"] = reasoning
        results.append(record)

    # Write output
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)

    # Print summary stats
    scores = [int(r["ai_score"]) for r in results if r.get("ai_score") is not None]
    total_jobs = 0
    weighted_num = 0
    for r in results:
        if r.get("ai_score") is not None and r.get("num_jobs"):
            try:
                s = int(r["ai_score"])
                j = int(r["num_jobs"])
                weighted_num += s * j
                total_jobs += j
            except (ValueError, TypeError):
                pass

    print(f"\nScoring complete!")
    print(f"  Total occupations scored: {len(scores)}")
    print(f"  Simple average: {sum(scores)/len(scores):.1f}")
    if total_jobs > 0:
        print(f"  Weighted avg (by employment): {weighted_num/total_jobs:.1f}")
        print(f"  Total jobs covered: {total_jobs:,}")
    print(f"  Min: {min(scores)}, Max: {max(scores)}")

    # Distribution
    from collections import Counter
    dist = Counter(scores)
    print("\n  Score distribution:")
    for s in range(11):
        count = dist.get(s, 0)
        bar = "#" * count
        print(f"    {s:2d}: {bar} ({count})")

    print(f"\nWrote to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
