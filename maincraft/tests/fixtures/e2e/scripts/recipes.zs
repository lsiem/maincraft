// Remove the default bronze ingot recipe
recipes.remove(<minecraft:bronze_ingot>);

// Add a shaped bronze recipe
recipes.addShaped(<minecraft:bronze_ingot>, [[<ore:ingotCopper>, <ore:ingotTin>]]);

// Remove a furnace recipe
recipes.removeFurnace(<minecraft:iron_block>);
