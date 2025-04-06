import csv

data = [
    ["Name", "Length", "Width", "Height", "Weight", "Quantity", "Fragility", "LoadBear", "BoxingType", "Bundle", "Temperature Sensitivity"],
    ["StandardPallet1", 1.2, 1, 1.2, 450, 2, "LOW", 1800, "PALLET", "YES", "10°C to 30°C"],
    ["HeavyMachinery", 2, 1.5, 1.8, 800, 1, "HIGH", 0, "CRATE", "NO", "n/a"],
    ["ElectronicCabinet", 0.8, 0.6, 1.8, 80, 2, "HIGH", 0, "CRATE", "NO", "n/a"],
    ["StorageBox", 1.2, 0.8, 0.6, 40, 4, "MEDIUM", 200, "CARTON", "YES", "0°C to 40°C"],
    ["IndustrialPump", 1, 0.8, 0.9, 150, 2, "MEDIUM", 400, "CRATE", "NO", "n/a"],
    ["SteelDrums", 0.6, 0.6, 0.9, 120, 3, "LOW", 600, "DRUM", "YES", "8°C to 25°C"],
    ["CardboardBoxes", 0.6, 0.4, 0.4, 10, 6, "LOW", 45, "CARTON", "YES", "10°C to 30°C"],
    ["WoodCrates", 1, 1, 1, 80, 2, "LOW", 300, "CRATE", "NO", "n/a"],
    ["PlasticContainers", 0.8, 0.6, 0.6, 25, 3, "LOW", 150, "BOX", "YES", "0°C to 40°C"],
    ["MachineParts", 1.2, 0.8, 0.8, 180, 2, "MEDIUM", 0, "CRATE", "NO", "n/a"],
    ["ToolBoxes", 0.5, 0.4, 0.3, 15, 4, "MEDIUM", 75, "BOX", "YES", "8°C to 25°C"],
    ["PackagedGoods", 0.6, 0.4, 0.5, 15, 6, "LOW", 100, "CARTON", "YES", "10°C to 30°C"],
    ["IndustrialFans", 0.8, 0.8, 1, 50, 3, "MEDIUM", 0, "CRATE", "NO", "n/a"],
    ["MetalFrames", 2.4, 0.8, 0.4, 100, 2, "LOW", 400, "FRAME", "NO", "n/a"],
    ["SafetyEquipment", 0.6, 0.4, 0.6, 20, 3, "HIGH", 0, "BOX", "NO", "n/a"],
    ["ChemicalBarrels", 0.6, 0.6, 1, 140, 2, "HIGH", 0, "DRUM", "NO", "n/a"],
    ["AutoParts", 1, 0.8, 0.6, 100, 3, "MEDIUM", 300, "CRATE", "YES", "0°C to 40°C"],
    ["PackagingSupplies", 1.2, 0.8, 0.4, 30, 4, "LOW", 200, "PALLET", "YES", "8°C to 25°C"],
    ["ElectricalBoxes", 0.4, 0.3, 0.5, 12, 4, "HIGH", 0, "BOX", "NO", "n/a"],
    ["LightFixtures", 1, 0.4, 0.2, 8, 6, "HIGH", 0, "BOX", "YES", "10°C to 30°C"]
]

with open('inventory_data_utf8.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    for row in data:
        writer.writerow(row)