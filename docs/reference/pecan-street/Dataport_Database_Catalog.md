# Dataport Database Catalog

## Schema name : audits_and_surveys

| Table Name | Description |
|---|---|
| audits_2011 | This table stores all of the information collected for the home energy audits performed by Pecan Street contractors in 2011. These audits were performed to fit the standards of the Austin, Texas Energy Conservation Audit and Disclosure (ECAD) Ordinance. |
| audits_2013_main | In 2013, Pecan Street began performing its own energy audits on participants’ homes. This table thus stores audits performed from 2013 onward. Each record in this table is the core portion of one energy audit, and it may have multiple associated records in the audits_2013_duct_leakage_eval and audits_2013_appliances tables. |
| audits_2013_appliances | Information was recorded regarding each major appliance in the homes audited by Pecan Street from 2013 onward, including the manufacturer and model number. Thus, there will be multiple appliance records in this table for each home energy audit. |
| audits_2013_duct_leakage_eval | A duct leakage evaluation was performed on each HVAC system of the audited homes. There may thus be one or more duct leakage evaluations in this table for each main audit record. |
| survey_2011_all_participants | This table stores the results of the 2011 Pecan Street general participant survey, which included demographic, appliance-related, and other types of questions. |
| survey_2012_all_participants | This table stores the results of the 2012 Pecan Street general participant survey. Questions on this survey asked about topics including demographics, home retrofits and upgrades, electricity use, water use, and transportation. |
| survey_2012_field_descriptions | This table matches column names from the 2012 survey data table with the actual text of the questions on the survey. |
| survey_2013_all_participants | This table stores the results of the 2013 Pecan Street general participant survey. Questions on this survey asked about topics including demographics, new technology adoption, appliances, and appliance use. |
| survey_2013_field_descriptions | This table matches column names from the 2013 survey data table with the actual text of the questions on the survey. |
| survey_2014_all_participants | This table stores the results of the 2014 Pecan Street general participant survey. The theme of this survey was photovoltaics, but other questions asked about demographics, household appliances, and appliance usage habits. |
| survey_2014_field_descriptions | This table matches column names from the 2014 survey data table with the actual text of the questions on the survey. |
| survey_2017_all_participants | This table stores the results of the 2017 Pecan Street general participant survey. |
| survey_2017_field_descriptions | This table matches column names from the 2017 survey data table with the actual text of the questions on the survey. |
| survey_2019_all_participants | This table stores the results of the 2019 Pecan Street general participant survey. Questions on this survey asked about topics including demographics, new technology adoption, appliances, and appliance use,electric vehicles etc. |
| survey_2019_field_descriptions | This table matches column names from the 2019 survey data table with the actual text of the questions on the survey. |

## Schema name : water_and_gas

| Table Name | Description |
|---|---|
| water_ert | This table stores water meter readings collected by ERT devices at the homes of Pecan Street participants. Three monitoring devices have been deployed: Itron Water Meters (April 2012 – May 2013), Digi ERT Gateways (July 2013 – February 2014), and Pecan Street ERT devices (April 2014 – present). Meter readings are cumulative and taken in gallons at irregular intervals; the Itron data averages about 1 reading per day, whereas the data from the Digi Gateways averages nearly one reading per minute. |
| gas_ert | This table stores gas meter readings collected by ERT devices at the homes of Pecan Street participants. Three monitoring devices have been deployed: Itron Gas Meters (April 2012 – May 2013), Digi ERT Gateways (July 2013 – February 2014), and Pecan Street ERT devices (April 2014 – present). Meter readings are cumulative and taken in cubic feet at irregular intervals; the Itron data averages about 1 reading per day, whereas the data from the Digi Gateways averages nearly one reading per minute. |
| blucube_water_data | This table stores water meter readings collected by Pecan Street blucube devices. These devices send reads multiple times every minute making this data more granular. |
| water_capstone | This table stores water data provided by Capstone meters during a meter project undertaken by Pecan Street. The water data has been converted into Gallons. |

## Schema name : electricity

Please note that this schema has only views and not tables.
All energy data for year 2012 - 2017  is only available in real power. From 2018 onwards energy data is available in real power, apparent power, current, phase angle and THD(Total Harmonic Distortion).

| View Name | Description |
|---|---|
| eg_realpower_1min | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in one-minute increments for year 2012 to present. All of the values in this table are average real power over the interval in kW. Timestamps indicate the starting time for the interval over which the data was measured. |
| eg_realpower_15min | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 15-minute increments. All of the values in this table are average real power over the interval in kW. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2012 to present. |
| eg_realpower_1s | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 1 second increments. All of the values in this table are average real power over the interval in kW. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2018 to present. |
| eg_realpower_1s_40homes_dataset | This dataset includes data collected by Pecan Street’s eGauge devices in 1-second increments for 40 homes.Every home has at least one year of data. This data was released in March 2018. For more information please check our blog here. |
| eg_apparentpower_1min | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 1-minute increments. All of the values in this table are average apparent power over the interval. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2018 onwards. |
| eg_apparentpower_15min | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 15-minute increments. All of the values in this table are average apparent power over the interval. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2018 onwards. |
| eg_apparentpower_1s | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 1-second increments. All of the values in this table are average apparent power over the interval. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2018 onwards. |
| eg_current_1min | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 1-minute increments. All of the values in this table are average current over the interval. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2018 onwards. |
| eg_current_15min | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 15-minute increments. All of the values in this table are average current over the interval. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2018 onwards. |
| eg_current_1s | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 1-second increments. All of the values in this table are average current over the interval. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2018 onwards. |
| eg_angle_1min | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 1-minute increments. All of the values in this table are average phase angle over the interval. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2018 onwards. |
| eg_angle_15min | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 15-minute increments. All of the values in this table are average phase angle over the interval. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2018 onwards. |
| eg_angle_1s | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 1-second increments. All of the values in this table are average phase angle over the interval. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2018 onwards. |
| eg_thd_1min | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 1-minute increments. All of the values in this table are average total harmonic distortion over the interval. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2018 onwards. |
| eg_thd_15min | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 15-minute increments. All of the values in this table are average total harmonic distortion over the interval. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2018 onwards. |
| eg_thd_1s | This view stores all of the electricity data collected by Pecan Street’s eGauge devices in 1-second increments. All of the values in this table are average total harmonic distortion over the interval. Timestamps indicate the starting time for the interval over which the data was measured.  This contains all data from year 2018 onwards. |

## Schema name : other_datasets

| Table Name | Description |
|---|---|
| civita_text_messages | This table stores the text messages data for the participants that were member of the Civita project. The participants received text messages asking them to conserve energy in various ways. |
| electric_vehicles | This table has a record for each electric vehicle in the possession of Pecan Street participants, where known. The vehicle’s make and model, model year, and date acquired by participant will be displayed here, if available. A few participants have more than one electric vehicle. |
| indoor_temperature_sensor | This table stores temperature readings from inside the home at 1-minute intervals. The temp_f column contains the temperature reading in Fahrenheit, while the temp_c column contains the temperature reading in Celsius. |
| pricing_events | This table lists all of the pricing events that occurred during the CCET pricing trial project. |
| pricing_events_notifications | This table lists all of the notifications sent out for each CCET pricing trial event. Each notification has its own unique ID. The pricing event ID indicates which pricing event the notification is associated with in the table above. The group name indicates which group of participants the notification was sent to: Pricing (CCET – Pricing Trial), General (CCET – Text Message), or Action (CCET – UT Text). |
| weather | This table contains weather data from Austin, Boulder, and San Diego, where the majority of Pecan Street’s participants are located. |
