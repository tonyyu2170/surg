# Metadata View Column Descriptions

For columns regarding eGauge circuits, if the field reads “yes”, there is data from the circuit in the eGauge data tables. If the field is blank, there is no data from the circuit in the eGauge data tables, although it is possible that the home has that type of circuit and it was not prioritized for monitoring.

| Column Name | Description |
| :--- | :--- |
| **dataid** | The unique identifier for the home. To be more precise, this is the unique identifier for the home resident pair. Thus, if a resident moves, the data collected from the house is associated with a new data ID. |
| **active_record** | This field will show “yes” if this participant is currently enrolled with Pecan Street and will be blank otherwise. |
| **building_type** | This field will read “Single-Family Home” if this is a freestanding single-family home, “Town Home” if it is a home that shares at least one wall with a neighboring house, or “Apartment” if it is an apartment. |
| **program_579** | This field will show “yes” if this participant is part of the 579 program and will be blank otherwise. The defining feature of the 579 program is that it includes participants in Texas outside the Austin area. |
| **program_baseline** | This field will show “yes” if this participant is part of the Baseline program and will be blank otherwise. Baseline program participants were part of a behavioral study in which they were not allowed to see their data for the first year of the study (2011-2012) and then were given a report with the details of their energy use. Data was collected for another year (2012-2013) for comparison, to see whether the participants reduced their energy use. |
| **program_energy_internet_demo** | This field will show “yes” if this participant is part of the Energy Internet Demonstration program, which includes most Austin, Texas participants enrolled prior to 2014. |
| **program_lg_appliance** | This field will show “yes” if this participant is part of the LG Appliance Trial and will be blank otherwise. These participants received new washers, dryers, and, in some cases, refrigerators as part of the trial. If the participant previously had a natural gas dryer monitored on their eGauge, it will have been replaced with an electric dryer at the time of the trial. |
| **program_verizon** | This field will show “yes” if this participant is part of the Verizon program, which involves exclusively residents of four low-income apartment complexes in Austin, Texas. Most of these participants do not have home internet access, so each household was given a tablet to facilitate their ability to view their energy use on their eGauge monitoring system from home. |
| **program_ccet_group** | This field will show one of the following group labels if the participant was a member of the CCET Trial: CCET – Control, CCET – Portal Only, CCET – Pricing Trial, CCET – Text Message, or CCET – UT Text. The Control group was not affected by or informed of the study. Portal Only participants received access to the special portal displaying their experimental account balance (and thus knowledge of how the experimental pricing scheme would have affected them), but they did not receive a financial incentive as part of the study. Pricing Trial participants received a financial incentive for shifting their electricity use away from peak hours on critical peak pricing days and shifting their electricity use toward wind-enhancement hours during the wind enhancement period of the study. They had access to a special portal that displayed their experimental account balance. Text Message participants received text messages asking them to reduce their energy consumption in general on peak days. UT Text participants received text messages asking them to restrict usage of specific appliances on peak days. |
| **program_civita_group** | This field will show one of the following group labels if the participant is a member of the Civita project: Civita – Control, or Civita – Text Message. Text Message participants received text messages asking them to conserve energy in various ways. Control group participants were not affected. |
| **city** | The city in which this residence is located. |
| **state** | The state in which this residence is located. |
| **pv** | This field will show “yes” if this participant has a solar photovoltaic system installed at their home and will be blank otherwise. |
| **date_enrolled** | The date on which this participant enrolled with Pecan Street. |
| **date_withdrawn** | The date on which this participant withdrew from participating with Pecan Street. If this field is blank, the participant is still enrolled. |
| **house_construction_year** | The year in which this home was constructed. |
| **total_square_footage** | The total square footage of the home. |
| **first_floor_square_footage** | The square footage of the first floor of the home. |
| **second_floor_square_footage** | The square footage of the second floor of the home. If this field is blank and this home’s first floor square footage is indicated, there is no second floor. If the first floor square footage is not indicated, the number of floors of the home is unknown. |
| **third_floor_square_footage** | The square footage of the third floor of the home. If this field is blank and this home’s first floor square footage is indicated, there is no third floor. If the first floor square footage is not indicated, the number of floors of the home is unknown. |
| **half_floor_square_footage** | The square footage of a half floor in the home. If this field is blank and this home’s first floor square footage is indicated, there is no half floor. If the first floor square footage is not indicated, the number of floors of the home is unknown. |
| **lower_level_square_footage** | The square footage of a lower level floor in the home. If this field is blank and this home’s first floor square footage is indicated, there is no lower level floor. If the first floor square footage is not indicated, the number of floors of the home is unknown. |
| **audit_2011** | This field will show “yes” if a 2011 home energy audit is available for this house. |
| **audit_2013_2014** | This field will show “yes” if a 2013 or later home energy audit is available for this house. |
| **survey_2011** | This field will show “yes” if this participant completed the annual Pecan Street survey in 2011 and will be blank otherwise. |
| **survey_2012** | This field will show “yes” if this participant completed the annual Pecan Street survey in 2012 and will be blank otherwise. |
| **survey_2013** | This field will show “yes” if this participant completed the annual Pecan Street survey in 2013 and will be blank otherwise. |
| **number_of_nests** | The number of Nest thermostats installed at the residence. If blank, this participant is not known to have a Nest thermostat in their home. |
| **indoor_temp_min_time** | If indoor temperature sensor data is present, this field will show the minimum timestamp of the available data. |
| **indoor_temp_max_time** | If indoor temperature sensor data is present, this field will show the maximum timestamp of the available data. |
| **gas_ert_min_time** | If ERT gas data is present, this field will show the minimum timestamp of the available data. |
| **gas_ert_max_time** | If ERT gas data is present, this field will show the maximum timestamp of the available data. |
| **water_ert_min_time** | If ERT water data is present, this field will show the minimum timestamp of the available data. |
| **water_ert_max_time** | If ERT water data is present, this field will show the maximum timestamp of the available data. |
| **egauge_min_time** | If eGauge electricity data is present, this field will show the minimum timestamp of the available data. |
| **egauge_max_time** | If eGauge electricity data is present, this field will show the maximum timestamp of the available data. |
| **air1** | Air compressor circuit eGauge data present. |
| **air2** | Second air compressor circuit eGauge data present. |
| **air3** | Third air compressor circuit eGauge data present. |
| **airwindowunit1** | Window unit air conditioner circuit eGauge data present. |
| **aquarium1** | Aquarium circuit eGauge data present. |
| **bathroom1** | First bathroom circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **bathroom2** | Second bathroom circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **bedroom1** | First bedroom circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **bedroom2** | Second bedroom circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **bedroom3** | Third bedroom circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **bedroom4** | Fourth bedroom circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **bedroom5** | Fifth bedroom circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **car1** | Electric vehicle charger eGauge data present. |
| **clotheswasher1** | Stand-alone clothes washing machine eGauge data present. |
| **clotheswasher_dryg1** | Clothes washing machine and natural gas-powered dryer circuit eGauge data present. |
| **diningroom1** | Dining room circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **diningroom2** | Additional dining room circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **dishwasher1** | Dishwasher circuit eGauge data present. |
| **disposal1** | Kitchen sink garbage disposal circuit eGauge data present. |
| **drye1** | Electricity-powered clothes dryer (240V circuit) eGauge data present. |
| **dryg1** | Natural gas-powered clothes dryer (120V circuit) eGauge data present. The eGauge will only pick up the electricity use from the dryer’s drum rotation, not the gas heating signature. |
| **freezer1** | Stand-alone freezer circuit eGauge data present. |
| **furnace1** | Furnace and air handler circuit eGauge data present. |
| **furnace2** | Second furnace and air handler eGauge data present. |
| **garage1** | Garage circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **garage2** | Additional garage circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **gen** | eGauge data present for power generated by a solar photovoltaic system. |
| **grid** | eGauge data present measuring power drawn from the electrical grid. grid = use - gen. |
| **heater1** | Stand-alone heater circuit eGauge data present. |
| **housefan1** | Whole home fan circuit eGauge data present. |
| **icemaker1** | Stand-alone icemaker circuit eGauge data present. |
| **jacuzzi1** | Jacuzzi bathtub or hot tub eGauge data present. |
| **kitchen1** | Kitchen circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **kitchen2** | Additional kitchen circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **kitchenapp1** | First kitchen small appliance circuit eGauge data present. This type of circuit includes only wall outlets in the kitchen, and so may include toasters, coffee makers, blenders, etc. |
| **kitchenapp2** | Second kitchen small appliance circuit eGauge data present. This type of circuit includes only wall outlets in the kitchen, and so may include toasters, coffee makers, blenders, etc. |
| **lights_plugs1** | General lighting and plugs circuit eGauge data present. This type of circuit includes lights, fans, and wall outlets, often from multiple rooms in the home. |
| **lights_plugs2** | Second general lighting and plugs circuit eGauge data present. This type of circuit includes lights, fans, and wall outlets, often from multiple rooms in the home. |
| **lights_plugs3** | Third general lighting and plugs circuit eGauge data present. This type of circuit includes lights, fans, and wall outlets, often from multiple rooms in the home. |
| **lights_plugs4** | Fourth general lighting and plugs circuit eGauge data present. This type of circuit includes lights, fans, and wall outlets, often from multiple rooms in the home. |
| **lights_plugs5** | Fifth general lighting and plugs circuit eGauge data present. This type of circuit includes lights, fans, and wall outlets, often from multiple rooms in the home. |
| **lights_plugs6** | Sixth lighting and plugs circuit eGauge data present. This type of circuit includes lights, fans, and wall outlets, often from multiple rooms in the home. |
| **livingroom1** | Living room circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **livingroom2** | Additional living room circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. |
| **microwave1** | Microwave circuit eGauge data present. |
| **office1** | Home office circuit eGauge data present. This type of circuit includes only lights, fans, and wall outlets. Computers may be common devices plugged into included any wall outlets included on this type of circuit. |
| **outsidelights_plugs1** | Exterior lighting and plugs circuit eGauge data present. |
| **outsidelights_plugs2** | Additional exterior lighting and plugs circuit eGauge data present. |
| **oven1** | Oven circuit eGauge data present. |
| **oven2** | Second oven circuit eGauge data present. |
| **pool1** | Combination pool pump and/or pool auxiliary power circuit eGauge data present. |
| **poollight1** | Pool lighting circuit eGauge data present. |
| **poolpump1** | Pool pump circuit eGauge data present. |
| **pump1** | eGauge data present for any type of pump that is not a pool pump. |
| **range1** | Range (either a stand-alone cooktop or a cooktop and an oven) circuit eGauge data present. |
| **refrigerator1** | Refrigerator circuit eGauge data present. |
| **refrigerator2** | Second refrigerator circuit eGauge data present. |
| **security1** | Security system circuit eGauge data present. |
| **shed1** | Shed circuit eGauge data present. |
| **sprinkler1** | Sprinkler system circuit eGauge data present. |
| **use** | Whole home electricity use eGauge data present. use = gen + grid. |
| **utilityroom1** | Utility room circuit eGauge data present. |
| **venthood1** | Vent hood circuit eGauge data present. |
| **waterheater1** | Electric water heater eGauge data present. |
| **waterheater2** | Second electric water heater eGauge data present. |
| **winecooler1** | Wine cooler circuit eGauge data present. |
