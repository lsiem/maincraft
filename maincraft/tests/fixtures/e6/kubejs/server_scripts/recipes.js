// Remove the default bronze ingot recipe
event.recipes.remove({output: 'minecraft:bronze_ingot'})

// Add a custom alloy recipe
event.recipes.custom('alloy_mix', ['minecraft:copper_ingot', 'minecraft:tin_ingot'])

// Replace input for iron dust
event.recipes.replaceInput({output: 'minecraft:iron_ingot'}, 'minecraft:iron_ore', 'minecraft:pulverized_iron');
