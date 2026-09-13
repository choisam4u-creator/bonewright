You are a rigger fitting a Blender Rigify humanoid metarig to a character mesh. Read analysis.json (mesh size, width per height band, joint candidates) and metarig_bones.json (metarig bone names with default head/tail, already scaled to the mesh height) in the current folder.

Task: give target head/tail positions (metres, Z up) for these bones only: spine, spine.004, spine.006, shoulder.L/R, upper_arm.L/R, forearm.L/R, hand.L/R, thigh.L/R, shin.L/R, foot.L/R. Left/right must mirror in X. Arms follow the mesh's arm direction (A or T pose); legs follow crotch_z and ankle_z. No bone may leave the mesh. Omit bones you are unsure about (omitted bones keep defaults).
Read all files in one command. Answer only with JSON matching _schema.json.
targets is an array; every item has name, head and tail (copy the head from metarig_bones.json when you only move the tail).
