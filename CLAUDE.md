# VITAICARE - Patient Monitoring Interface

## Project Overview

**Full Title**: Design and implementation of a user interface for the visualization of biometric data obtained through smartwatches, aimed at improving medical team decision-making in the monitoring of institutionalized elderly people.

**Project Type**: Final Career Project (Bioengineering)
**Institution**: Instituto Tecnológico de Buenos Aires (ITBA)
**Student**: Rocío Pesoa
**Advisor**: Giuliana Espósito
**Timeline**: November 2024 - April 2025
**Delivery Date**: December 1, 2025

## Project Context

This project is part of a collaborative initiative between:
- Universidad de Alcalá (UAH), Spain
- Medical team at Residencia Asturiana de Buenos Aires
- Instituto Tecnológico de Buenos Aires (ITBA)

### Problem Statement

Institutionalized elderly people require close clinical monitoring to detect health changes early and prevent complications. Currently, medical teams work with fragmented information across different systems with limited systematic data exploitation.

This project addresses the critical need for a clear, usable, and clinically relevant user interface that allows medical staff to:
1. Clearly visualize temporal evolution of physiological variables for each resident
2. Identify deviations from usual patterns for each patient
3. Relate variable changes with relevant clinical events (infections, decompensations, etc.)

## Technical Overview

### Hardware
- **Smartwatch Model**: ID Vita - Telecare Smartwatch (Intelligent Data)
- **Sensors**: Heart rate, oxygen saturation, temperature, blood pressure
- **Additional Data**: Self-perceived status, activity levels
- **Storage**: Memory card for periodic data storage and analysis

### Monitored Variables
- Heart rate (HR)
- Oxygen saturation (SpO2)
- Body temperature
- Blood pressure
- Self-perceived health status
- Activity patterns
- Rest patterns

### Technology Stack
- **Backend**: Database servers storing telemonitoring records and clinical information
- **Frontend**: Python-based interface (prototyping and development)
- **Data Analysis**: Python for statistical analysis, usability testing results, and visualizations
- **Data Access**: Predefined queries/services to feed the visualization interface

## Project Objectives

### General Objective
Design, implement, and evaluate a user interface for visualizing physiological variables and activity parameters recorded by smartwatches in institutionalized elderly people at Residencia Asturiana de Buenos Aires.

### Minimum Objectives
1. **Device Traceability**: Organize and ensure traceability of measurement devices
2. **Requirements Gathering**: Survey clinical and visualization requirements from the Residence health team:
   - Identify priority variables
   - Determine optimal time ranges for different variables
   - Define most intuitive graph types for measurement comparisons
3. **Architecture Definition**: Define functional architecture, number of modules, main views, and basic indicator set
4. **Prototype Development**: Develop functional user interface prototype allowing visualization of physiological variables and temporal event series for each resident
5. **Data Integration**: Integrate data from the Residencia Asturiana database into the user interface

### Maximum Objectives (Stretch Goals)
1. **Scalability Recommendations**: Propose recommendations for scaling the visualization platform to other elderly care centers
2. **Comparative Analysis**: Exploratory comparison of monitoring patterns and biometric data usage between local residence and Universidad de Alcalá (UAH) research center in Spain

## Methodology

### 1. Requirements Gathering
- Short interviews/meetings with health team to understand:
  - Most relevant variables for daily monitoring
  - Preferred temporal horizons for queries
  - Useful summaries, comparisons, and alerts

### 2. Requirements Definition & Functional Structure
- Establish prioritized function list
- Define main interface views

### 3. Interface Design
- Create initial prototypes for user presentation
- Incorporate adjustments based on feedback
- Develop detailed prototypes as implementation guide

### 4. Functional Prototype Development
- Implement interface connected to data source
- Build temporal evolution graphs, indicator panels, and clinical event timeline representations

### 5. Usability Evaluation
- Define representative real-world tasks
- Observe participants using the platform
- Record: task completion time, difficulties/errors, user opinions
- Iterative user-centered design process
- Apply usability surveys with Likert scale items for user experience metrics

### 6. Results Analysis & Synthesis
- Process times, errors, and survey responses
- Identify usage patterns, interface strengths and weaknesses
- Formulate improvement points for future versions

## Project Timeline (Gantt Chart Summary)

| Phase | Timeline | Key Activities |
|-------|----------|----------------|
| **Literature Review & Protocol Design** | November 2024 | Specific bibliographic review, requirements gathering protocol design |
| **Planning & Architecture** | December 2024 | Detailed planning, initial interface sketches, technical architecture definition |
| **Interviews & Iterative Design** | January 2025 | Interviews/workshops with medical team, requirements analysis, high-fidelity prototypes |
| **Final Implementation** | February 2025 | Final view selection, representation methods, functional prototype implementation |
| **Testing & Validation** | March 2025 | Dataset integration, internal testing, usability study execution with professionals, data collection and analysis |
| **Results & Conclusions** | April 2025 | Results consolidation, conclusions formulation |

## Theoretical Framework

The project is organized around four main theoretical axes:

### 1. Telemonitoring and Digital Health in Elderly People
- Review of remote monitoring experiences in long-stay institutions
- Use of wearable devices for vital signs, daily activity, and clinical deterioration events
- Similar monitoring programs in residential settings

### 2. Physiological and Activity Variables from Wearable Devices
- Main parameters measurable with smartwatches
- Clinical relevance in elderly populations
- Standard temporal representation methods

### 3. Clinical Interface Design and Data Visualization for Health Teams
- User-centered design concepts for health professionals
- Legibility criteria and cognitive load
- Recommended graph types for vital sign time series
- Patient monitoring dashboard examples in care settings

### 4. Project Management and Evaluation in Bioengineering for Healthcare
- Reference frameworks for planning and executing health technology projects
- Strategies for integrating prototype developments in real institutions
- Organizational aspects and adoption by healthcare personnel

## Ethical Considerations

- **Data Anonymization**: Resident data used for the platform will be anonymized to prevent identification of individuals by students or third parties
- **Protocol Compliance**: Respect institution and research project protocols regarding confidentiality, secure information storage, and restricted access
- **Voluntary Participation**: Health personnel participation in interviews and usability tests is voluntary with clear information about study objectives and results usage

## Project Resources

### Available Resources (Provided by Institutions)
- Smartwatches and sensors
- Network infrastructure
- Computer equipment
- Database servers

### Project-Specific Costs
| Item | Description | Quantity | Unit Cost | Total Cost |
|------|-------------|----------|-----------|------------|
| Hardware | 2TB external hard drive for data backup | 1 | $260,000 ARS | $260,000 ARS |

**Total Budget**: $260,000 ARS

## Project Location
- **Primary**: Instituto Tecnológico de Buenos Aires (ITBA)
- **Field Site**: Residencia Asturiana de Buenos Aires

## Project Team

### Tutors
- **Dr. Miguel Aguirre** (ITBA)
- **Ing. Melisa Granda** (UAH)

### Student
- **Rocío Pesoa** (ITBA - Bioengineering)

### Collaborating Professor
- **Giuliana Espósito**

## Key References

1. Manual del reloj ID Vita - Manual de usuario
2. M. Clark, "Single-Use Wearable Wireless Sensors for Vital Sign Monitoring," Canadian Journal of Health Technologies, 2023
3. K. Moore et al., "Older Adults' Experiences With Using Wearable Devices," JMIR mHealth and uHealth, 2021
4. S. S. Khairat et al., "The Impact of Visualization Dashboards on Quality of Care," JMIR Human Factors, 2018
5. D. Dowding et al., "Usability Evaluation of a Dashboard for Home Care Nurses," CIN: Computers, Informatics, Nursing, 2019

## Development Guidelines for Claude

### Core Principles
1. **User-Centered Design**: All interface decisions must prioritize medical staff workflow and usability
2. **Clinical Relevance**: Focus on visualizations that support real decision-making
3. **Data Clarity**: Ensure clear, intuitive presentation of complex temporal data
4. **Simplicity**: Avoid over-engineering; build what is directly requested or clearly necessary
5. **Privacy First**: Always maintain data anonymization and security protocols

### Technical Approach
- Use Python for rapid prototyping and development
- Design for scalability to other elderly care centers
- Implement iterative development cycles with medical team feedback
- Focus on time-series visualizations of physiological variables
- Enable easy comparison of individual patient patterns over time
- Support identification of deviations from baseline patterns

### Expected Deliverables
1. Functional user interface prototype
2. Device traceability system
3. Integration with existing database
4. Usability evaluation results
5. Documentation and recommendations for future scaling

### Key Features to Implement
- **Patient Dashboard**: Individual view for each resident with all their physiological data
- **Time-Series Graphs**: Interactive visualization of variables over time (heart rate, SpO2, temperature, blood pressure)
- **Pattern Detection**: Visual indicators for deviations from individual baselines
- **Event Timeline**: Clinical events correlated with physiological data changes
- **Comparative Views**: Ability to compare multiple variables or time periods
- **Alert System**: Notifications for significant deviations or concerning patterns
- **Device Management**: Traceability system linking devices to patients and usage periods

---

**Last Updated**: January 22, 2026
**Project Status**: In Development (newpacientes module)
