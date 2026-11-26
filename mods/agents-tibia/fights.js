// What a working agent fights: a monster and a spell, drawn independently and
// kept for that working stretch. The monster stays for what follows: cornering
// the character, or lying dead once the agent is done. tools/tibia860.py reads
// both tables to render the fight sprites.
// [monster looktype, corpse item id]
export const MONSTERS = [
  [34, 5973],   // dragon
  [35, 5995],   // demon
  [22, 5962],   // cyclops
  [5, 5966],    // orc
  [38, 5977],   // giant spider
  [121, 6048],  // hydra
  [26, 5967],   // rotworm
  [33, 5972],   // skeleton
];

// [missile id, hit effect id]
export const SPELLS = [
  [29, 44], // ice
  [31, 49], // holy burst
  [4, 16],  // fire
  [5, 12],  // energy
  [36, 11], // energy ball
  [32, 18], // sudden death
  [30, 9],  // earth
  [38, 40], // small holy
];
