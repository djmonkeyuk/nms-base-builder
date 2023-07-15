Order of steps to get the tool up to date.

1. Generate a new list of nice name via the nicename_generator.py
2. Print a missing report via the part_generator/MissingPartReport.bat file.
3. Copy the missing path items into the DT_PartTable excel file.
4. Keep generating the MissingPartReport until all red items become green.
5. Execute the GenerateMissingOBJ.bat to start creating all the missing 3D objects. This will take a while as it uses Blender in batch mode.
6. Run the generate_partdefinition.py file to get the DT_PartDefinition.csv file up to date. Be careful as any edits in Unreal would need to be re-exported to this file first.
7. For Unreal, copy over any new objs and the DT_PartDefiniton file back into the project.