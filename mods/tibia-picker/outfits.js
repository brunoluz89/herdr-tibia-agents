// A copy of agents-tibia/outfits.js (a mod cannot import another mod's code); install.py checks they match.
// The outfits the picker offers, as [name, male looktype, female looktype].
// tools/tibia860.py reads the looktypes of both tables to render each character.
export const OUTFITS = [
  ["Citizen", 128, 136],
  ["Hunter", 129, 137],
  ["Mage", 130, 138],
  ["Knight", 131, 139],
  ["Noble", 132, 140],
  ["Summoner", 133, 141],
  ["Warrior", 134, 142],
  ["Barbarian", 143, 147],
  ["Druid", 144, 148],
  ["Wizard", 145, 149],
  ["Oriental", 146, 150],
  ["Pirate", 151, 155],
  ["Assassin", 152, 156],
  ["Beggar", 153, 157],
  ["Shaman", 154, 158],
  ["Norse", 251, 252],
  ["Nightmare", 268, 269],
  ["Jester", 273, 270],
  ["Brotherhood", 278, 279],
  ["Demon Hunter", 289, 288],
  ["Yalaharian", 325, 324],
  ["Newly Wed", 328, 329],
  ["Warmaster", 335, 336],
  ["Wayfarer", 367, 366],
];

// The oldschool looks of the first seven, shown in their own row.
export const RETRO = [
  ["Citizen", 974, 975],
  ["Hunter", 972, 973],
  ["Mage", 968, 969],
  ["Knight", 970, 971],
  ["Noble", 966, 967],
  ["Summoner", 964, 965],
  ["Warrior", 962, 963],
];
