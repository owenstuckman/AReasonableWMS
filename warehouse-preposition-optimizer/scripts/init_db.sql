-- Warehouse Pre-Positioning Optimizer: Database Initialization
-- Creates and seeds tables for the WMS adapter

-- ──────────────────────────────────────────────────────────────────────────────
-- LOCATIONS
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS locations (
    location_id        VARCHAR(50) PRIMARY KEY,
    zone               VARCHAR(20) NOT NULL,
    aisle              INTEGER     NOT NULL,
    bay                INTEGER     NOT NULL,
    level              INTEGER     NOT NULL DEFAULT 0,
    x                  NUMERIC(8,2) NOT NULL,
    y                  NUMERIC(8,2) NOT NULL,
    temperature_zone   VARCHAR(20) NOT NULL DEFAULT 'AMBIENT',
    max_weight_kg      NUMERIC(8,2) NOT NULL DEFAULT 2000.0,
    max_volume_m3      NUMERIC(8,2) NOT NULL DEFAULT 10.0,
    is_staging         BOOLEAN     NOT NULL DEFAULT FALSE,
    nearest_dock_door  INTEGER
);

-- Seed: 3 zones (A, B, C) with 30 regular locations + 8 staging + 2 frozen + 4 chilled
INSERT INTO locations (location_id, zone, aisle, bay, level, x, y, temperature_zone, max_weight_kg, max_volume_m3, is_staging, nearest_dock_door) VALUES
-- Zone A (10 locations)
('LOC-A01', 'A', 1, 1, 0,  20.0,  5.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-A02', 'A', 1, 2, 0,  25.0,  5.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-A03', 'A', 1, 3, 0,  30.0,  5.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-A04', 'A', 2, 1, 0,  20.0, 10.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-A05', 'A', 2, 2, 0,  25.0, 10.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-A06', 'A', 2, 3, 0,  30.0, 10.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-A07', 'A', 3, 1, 0,  20.0, 15.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-A08', 'A', 3, 2, 0,  25.0, 15.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-A09', 'A', 3, 3, 0,  30.0, 15.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-A10', 'A', 3, 4, 0,  35.0, 15.0, 'AMBIENT', 2000, 10, FALSE, NULL),
-- Zone B (10 locations)
('LOC-B01', 'B', 4, 1, 0,  45.0,  5.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-B02', 'B', 4, 2, 0,  50.0,  5.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-B03', 'B', 4, 3, 0,  55.0,  5.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-B04', 'B', 5, 1, 0,  45.0, 10.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-B05', 'B', 5, 2, 0,  50.0, 10.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-B06', 'B', 5, 3, 0,  55.0, 10.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-B07', 'B', 6, 1, 0,  45.0, 15.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-B08', 'B', 6, 2, 0,  50.0, 15.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-B09', 'B', 6, 3, 0,  55.0, 15.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-B10', 'B', 6, 4, 0,  60.0, 15.0, 'AMBIENT', 2000, 10, FALSE, NULL),
-- Zone C (10 locations)
('LOC-C01', 'C', 7, 1, 0,  70.0,  5.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-C02', 'C', 7, 2, 0,  75.0,  5.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-C03', 'C', 7, 3, 0,  80.0,  5.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-C04', 'C', 8, 1, 0,  70.0, 10.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-C05', 'C', 8, 2, 0,  75.0, 10.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-C06', 'C', 8, 3, 0,  80.0, 10.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-C07', 'C', 9, 1, 0,  70.0, 15.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-C08', 'C', 9, 2, 0,  75.0, 15.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-C09', 'C', 9, 3, 0,  80.0, 15.0, 'AMBIENT', 2000, 10, FALSE, NULL),
('LOC-C10', 'C', 9, 4, 0,  85.0, 15.0, 'AMBIENT', 2000, 10, FALSE, NULL),
-- Cold storage (2 frozen, 4 chilled)
('LOC-COLD01', 'COLD', 10, 1, 0,  90.0,  5.0, 'FROZEN',  1500,  8, FALSE, NULL),
('LOC-COLD02', 'COLD', 10, 2, 0,  90.0, 10.0, 'FROZEN',  1500,  8, FALSE, NULL),
('LOC-CHILL01', 'COLD', 11, 1, 0, 95.0,  5.0, 'CHILLED', 1800,  9, FALSE, NULL),
('LOC-CHILL02', 'COLD', 11, 2, 0, 95.0, 10.0, 'CHILLED', 1800,  9, FALSE, NULL),
('LOC-CHILL03', 'COLD', 11, 3, 0, 95.0, 15.0, 'CHILLED', 1800,  9, FALSE, NULL),
('LOC-CHILL04', 'COLD', 11, 4, 0, 95.0, 20.0, 'CHILLED', 1800,  9, FALSE, NULL),
-- Staging locations near dock doors (4 dock doors: 1, 2, 3, 4)
('STAGE-D1-A', 'STAGING', 12, 1, 0,  2.0,  5.0, 'AMBIENT', 2500, 12, TRUE, 1),
('STAGE-D1-B', 'STAGING', 12, 2, 0,  2.0, 10.0, 'AMBIENT', 2500, 12, TRUE, 1),
('STAGE-D2-A', 'STAGING', 13, 1, 0,  2.0, 15.0, 'AMBIENT', 2500, 12, TRUE, 2),
('STAGE-D2-B', 'STAGING', 13, 2, 0,  2.0, 20.0, 'AMBIENT', 2500, 12, TRUE, 2),
('STAGE-D3-A', 'STAGING', 14, 1, 0,  2.0, 25.0, 'AMBIENT', 2500, 12, TRUE, 3),
('STAGE-D3-B', 'STAGING', 14, 2, 0,  2.0, 30.0, 'AMBIENT', 2500, 12, TRUE, 3),
('STAGE-D4-A', 'STAGING', 15, 1, 0,  2.0, 35.0, 'AMBIENT', 2500, 12, TRUE, 4),
('STAGE-D4-B', 'STAGING', 15, 2, 0,  2.0, 40.0, 'AMBIENT', 2500, 12, TRUE, 4);

-- ──────────────────────────────────────────────────────────────────────────────
-- SKUS
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS skus (
    sku_id                    VARCHAR(50) PRIMARY KEY,
    description               TEXT        NOT NULL,
    weight_kg                 NUMERIC(8,3) NOT NULL,
    volume_m3                 NUMERIC(8,4) NOT NULL,
    hazmat_class              VARCHAR(10),
    requires_temperature_zone VARCHAR(20) NOT NULL DEFAULT 'AMBIENT',
    abc_class                 CHAR(1)     NOT NULL DEFAULT 'C'
);

-- Seed: 50 SKUs (mix of ABC, temperatures, some hazmat)
INSERT INTO skus (sku_id, description, weight_kg, volume_m3, hazmat_class, requires_temperature_zone, abc_class) VALUES
-- Class A ambient SKUs (high velocity)
('SKU-A001', 'Widget Type A - High Velocity',       45.0,  0.250, NULL, 'AMBIENT', 'A'),
('SKU-A002', 'Component B Assembly',               120.0,  0.600, NULL, 'AMBIENT', 'A'),
('SKU-A003', 'Packaging Material Roll',             15.0,  0.800, NULL, 'AMBIENT', 'A'),
('SKU-A004', 'Electronic Module X200',              8.5,   0.040, NULL, 'AMBIENT', 'A'),
('SKU-A005', 'Consumer Goods Unit P',              30.0,   0.200, NULL, 'AMBIENT', 'A'),
('SKU-A006', 'Retail Box Assembly RB',             22.0,   0.180, NULL, 'AMBIENT', 'A'),
('SKU-A007', 'Bulk Powder Container',              200.0,  1.000, NULL, 'AMBIENT', 'A'),
('SKU-A008', 'Automotive Part AF-12',              85.0,   0.400, NULL, 'AMBIENT', 'A'),
('SKU-A009', 'Standard Pallet Load SL',            500.0,  2.000, NULL, 'AMBIENT', 'A'),
('SKU-A010', 'Fast-Moving Consumer Good',          18.0,   0.120, NULL, 'AMBIENT', 'A'),
-- Class B ambient SKUs (medium velocity)
('SKU-B001', 'Medium Velocity Widget',             60.0,   0.350, NULL, 'AMBIENT', 'B'),
('SKU-B002', 'Industrial Component IC-7',          150.0,  0.750, NULL, 'AMBIENT', 'B'),
('SKU-B003', 'Spare Part Assembly SP-23',           35.0,  0.220, NULL, 'AMBIENT', 'B'),
('SKU-B004', 'Tool Kit TK-Standard',               12.0,   0.060, NULL, 'AMBIENT', 'B'),
('SKU-B005', 'Office Supply Bundle OS',             5.0,   0.030, NULL, 'AMBIENT', 'B'),
('SKU-B006', 'Machine Sub-Assembly MSA',           300.0,  1.500, NULL, 'AMBIENT', 'B'),
('SKU-B007', 'Textile Roll TR-100',                80.0,   0.900, NULL, 'AMBIENT', 'B'),
('SKU-B008', 'Plastic Component PC-45',            25.0,   0.150, NULL, 'AMBIENT', 'B'),
('SKU-B009', 'Metal Bracket MB-12',                40.0,   0.200, NULL, 'AMBIENT', 'B'),
('SKU-B010', 'Rubber Seal RS-8',                    2.0,   0.010, NULL, 'AMBIENT', 'B'),
-- Class C ambient SKUs (low velocity)
('SKU-C001', 'Slow Mover SC-001',                  70.0,  0.400, NULL, 'AMBIENT', 'C'),
('SKU-C002', 'Archived Document Box',              10.0,  0.500, NULL, 'AMBIENT', 'C'),
('SKU-C003', 'Legacy Part LP-99',                 180.0,  0.900, NULL, 'AMBIENT', 'C'),
('SKU-C004', 'Surplus Material SM-7',              55.0,  0.300, NULL, 'AMBIENT', 'C'),
('SKU-C005', 'Overflow Stock OV-3',                90.0,  0.450, NULL, 'AMBIENT', 'C'),
-- Frozen SKUs
('SKU-F001', 'Frozen Meal Tray FM-1',              8.0,   0.040, NULL, 'FROZEN',  'A'),
('SKU-F002', 'Ice Cream Carton IC-2L',             2.5,   0.002, NULL, 'FROZEN',  'A'),
('SKU-F003', 'Frozen Vegetable Pack FV',           1.0,   0.001, NULL, 'FROZEN',  'B'),
('SKU-F004', 'Frozen Protein Portion PP',          5.0,   0.005, NULL, 'FROZEN',  'B'),
('SKU-F005', 'Bulk Frozen Commodity BF',          50.0,   0.050, NULL, 'FROZEN',  'C'),
-- Chilled SKUs
('SKU-CH001', 'Fresh Dairy Product DP',            3.0,  0.003, NULL, 'CHILLED', 'A'),
('SKU-CH002', 'Chilled Juice Carton CJ',           1.5,  0.001, NULL, 'CHILLED', 'A'),
('SKU-CH003', 'Yogurt Multipack YM',               0.8,  0.001, NULL, 'CHILLED', 'B'),
('SKU-CH004', 'Prepared Meal Kit PMK',             4.5,  0.004, NULL, 'CHILLED', 'B'),
('SKU-CH005', 'Cold Cut Deli Pack CD',             2.0,  0.002, NULL, 'CHILLED', 'C'),
-- Hazmat SKUs
('SKU-HZ001', 'Industrial Solvent IS-1',           30.0, 0.025, '3',   'AMBIENT', 'B'),
('SKU-HZ002', 'Cleaning Chemical CC-8',            25.0, 0.020, '8',   'AMBIENT', 'C'),
('SKU-HZ003', 'Compressed Gas Cylinder CG',        50.0, 0.100, '2',   'AMBIENT', 'C'),
('SKU-HZ004', 'Battery Pack BP-LiIon',             15.0, 0.010, '9',   'AMBIENT', 'B'),
('SKU-HZ005', 'Oxidizing Agent OA-15',             20.0, 0.018, '5.1', 'AMBIENT', 'C'),
-- Additional Class A ambient SKUs
('SKU-A011', 'Fast Mover Product FM11',            40.0, 0.210, NULL, 'AMBIENT', 'A'),
('SKU-A012', 'Priority SKU PR-12',                 55.0, 0.290, NULL, 'AMBIENT', 'A'),
('SKU-A013', 'High Demand Item HD-13',             72.0, 0.380, NULL, 'AMBIENT', 'A'),
('SKU-A014', 'Velocity Leader VL-14',             110.0, 0.550, NULL, 'AMBIENT', 'A'),
('SKU-A015', 'Top Seller TS-15',                   28.0, 0.160, NULL, 'AMBIENT', 'A'),
('SKU-B011', 'Medium Mover MM-11',                 65.0, 0.340, NULL, 'AMBIENT', 'B'),
('SKU-B012', 'Standard Volume SV-12',             105.0, 0.520, NULL, 'AMBIENT', 'B'),
('SKU-B013', 'Regular Product RP-13',              42.0, 0.230, NULL, 'AMBIENT', 'B'),
('SKU-B014', 'Planned Order PO-14',                88.0, 0.430, NULL, 'AMBIENT', 'B'),
('SKU-B015', 'Seasonal Item SI-15',                35.0, 0.190, NULL, 'AMBIENT', 'B');

-- ──────────────────────────────────────────────────────────────────────────────
-- INVENTORY POSITIONS
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inventory_positions (
    position_id  VARCHAR(50) PRIMARY KEY,
    sku_id       VARCHAR(50) NOT NULL REFERENCES skus(sku_id),
    location_id  VARCHAR(50) NOT NULL REFERENCES locations(location_id),
    quantity     INTEGER     NOT NULL DEFAULT 0,
    lot_number   VARCHAR(50),
    expiry_date  TIMESTAMPTZ
);

-- Seed: Place SKUs in appropriate locations
INSERT INTO inventory_positions (position_id, sku_id, location_id, quantity, lot_number, expiry_date) VALUES
-- Zone A locations (fast-moving ambient)
('INV-001', 'SKU-A001', 'LOC-A01', 50, 'LOT-2024-001', NULL),
('INV-002', 'SKU-A002', 'LOC-A02', 20, 'LOT-2024-002', NULL),
('INV-003', 'SKU-A003', 'LOC-A03', 100,'LOT-2024-003', NULL),
('INV-004', 'SKU-A004', 'LOC-A04', 200,'LOT-2024-004', NULL),
('INV-005', 'SKU-A005', 'LOC-A05', 75, 'LOT-2024-005', NULL),
('INV-006', 'SKU-A006', 'LOC-A06', 60, 'LOT-2024-006', NULL),
('INV-007', 'SKU-A007', 'LOC-A07', 15, 'LOT-2024-007', NULL),
('INV-008', 'SKU-A008', 'LOC-A08', 30, 'LOT-2024-008', NULL),
('INV-009', 'SKU-A009', 'LOC-A09', 10, 'LOT-2024-009', NULL),
('INV-010', 'SKU-A010', 'LOC-A10', 120,'LOT-2024-010', NULL),
-- Zone B (medium velocity)
('INV-011', 'SKU-B001', 'LOC-B01', 40, 'LOT-2024-011', NULL),
('INV-012', 'SKU-B002', 'LOC-B02', 12, 'LOT-2024-012', NULL),
('INV-013', 'SKU-B003', 'LOC-B03', 55, 'LOT-2024-013', NULL),
('INV-014', 'SKU-B004', 'LOC-B04', 80, 'LOT-2024-014', NULL),
('INV-015', 'SKU-B005', 'LOC-B05', 300,'LOT-2024-015', NULL),
('INV-016', 'SKU-B006', 'LOC-B06', 8,  'LOT-2024-016', NULL),
('INV-017', 'SKU-B007', 'LOC-B07', 5,  'LOT-2024-017', NULL),
('INV-018', 'SKU-B008', 'LOC-B08', 90, 'LOT-2024-018', NULL),
('INV-019', 'SKU-B009', 'LOC-B09', 45, 'LOT-2024-019', NULL),
('INV-020', 'SKU-B010', 'LOC-B10', 500,'LOT-2024-020', NULL),
-- Zone C (slow moving)
('INV-021', 'SKU-C001', 'LOC-C01', 25, 'LOT-2024-021', NULL),
('INV-022', 'SKU-C002', 'LOC-C02', 18, 'LOT-2024-022', NULL),
('INV-023', 'SKU-C003', 'LOC-C03', 7,  'LOT-2024-023', NULL),
('INV-024', 'SKU-C004', 'LOC-C04', 33, 'LOT-2024-024', NULL),
('INV-025', 'SKU-C005', 'LOC-C05', 14, 'LOT-2024-025', NULL),
-- Cold storage
('INV-026', 'SKU-F001', 'LOC-COLD01', 200, 'LOT-FROZEN-001', (NOW() + INTERVAL '90 days')),
('INV-027', 'SKU-F002', 'LOC-COLD01', 150, 'LOT-FROZEN-002', (NOW() + INTERVAL '60 days')),
('INV-028', 'SKU-F003', 'LOC-COLD02', 300, 'LOT-FROZEN-003', (NOW() + INTERVAL '45 days')),
('INV-029', 'SKU-CH001','LOC-CHILL01',100, 'LOT-CHILL-001',  (NOW() + INTERVAL '14 days')),
('INV-030', 'SKU-CH002','LOC-CHILL02', 80, 'LOT-CHILL-002',  (NOW() + INTERVAL '10 days')),
-- Hazmat (in Zone C, away from main flow)
('INV-031', 'SKU-HZ001', 'LOC-C06',  20, 'LOT-HAZ-001', NULL),
('INV-032', 'SKU-HZ002', 'LOC-C07',  15, 'LOT-HAZ-002', NULL),
('INV-033', 'SKU-HZ003', 'LOC-C08',  10, 'LOT-HAZ-003', NULL),
-- Additional A/B class
('INV-034', 'SKU-A011', 'LOC-A01', 35, 'LOT-2024-034', NULL),
('INV-035', 'SKU-A012', 'LOC-A02', 22, 'LOT-2024-035', NULL),
('INV-036', 'SKU-A013', 'LOC-B01', 18, 'LOT-2024-036', NULL),
('INV-037', 'SKU-A014', 'LOC-B02', 11, 'LOT-2024-037', NULL),
('INV-038', 'SKU-A015', 'LOC-B03', 60, 'LOT-2024-038', NULL),
('INV-039', 'SKU-B011', 'LOC-B04', 28, 'LOT-2024-039', NULL),
('INV-040', 'SKU-B012', 'LOC-B05', 16, 'LOT-2024-040', NULL);

-- ──────────────────────────────────────────────────────────────────────────────
-- CARRIER APPOINTMENTS
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS carrier_appointments (
    appointment_id      VARCHAR(50) PRIMARY KEY,
    carrier             VARCHAR(100) NOT NULL,
    dock_door           INTEGER      NOT NULL,
    scheduled_arrival   TIMESTAMPTZ  NOT NULL,
    scheduled_departure TIMESTAMPTZ  NOT NULL,
    status              VARCHAR(20)  NOT NULL DEFAULT 'SCHEDULED'
);

-- Seed: 4 appointments for today
INSERT INTO carrier_appointments (appointment_id, carrier, dock_door, scheduled_arrival, scheduled_departure, status) VALUES
('APPT-TODAY-001', 'ACME Freight',       1, (NOW() + INTERVAL  '2 hours'), (NOW() + INTERVAL  '3 hours'), 'SCHEDULED'),
('APPT-TODAY-002', 'FastShip Logistics', 2, (NOW() + INTERVAL  '4 hours'), (NOW() + INTERVAL  '5 hours'), 'SCHEDULED'),
('APPT-TODAY-003', 'Priority Carrier',   3, (NOW() + INTERVAL  '6 hours'), (NOW() + INTERVAL  '7 hours'), 'SCHEDULED'),
('APPT-TODAY-004', 'RegionalX Express',  4, (NOW() + INTERVAL '10 hours'), (NOW() + INTERVAL '11 hours'), 'SCHEDULED');

-- ──────────────────────────────────────────────────────────────────────────────
-- OUTBOUND ORDERS
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS outbound_orders (
    order_id       VARCHAR(50)  PRIMARY KEY,
    appointment_id VARCHAR(50)  NOT NULL REFERENCES carrier_appointments(appointment_id),
    priority       INTEGER      NOT NULL DEFAULT 5,
    cutoff_time    TIMESTAMPTZ  NOT NULL
);

INSERT INTO outbound_orders (order_id, appointment_id, priority, cutoff_time) VALUES
('ORD-0001', 'APPT-TODAY-001', 8,  (NOW() + INTERVAL  '2 hours 30 minutes')),
('ORD-0002', 'APPT-TODAY-001', 7,  (NOW() + INTERVAL  '2 hours 45 minutes')),
('ORD-0003', 'APPT-TODAY-002', 5,  (NOW() + INTERVAL  '4 hours 30 minutes')),
('ORD-0004', 'APPT-TODAY-002', 6,  (NOW() + INTERVAL  '4 hours 45 minutes')),
('ORD-0005', 'APPT-TODAY-003', 4,  (NOW() + INTERVAL  '6 hours 30 minutes')),
('ORD-0006', 'APPT-TODAY-003', 9,  (NOW() + INTERVAL  '6 hours 15 minutes')),
('ORD-0007', 'APPT-TODAY-004', 3,  (NOW() + INTERVAL '10 hours 30 minutes')),
('ORD-0008', 'APPT-TODAY-004', 5,  (NOW() + INTERVAL '10 hours 45 minutes')),
('ORD-0009', 'APPT-TODAY-001', 10, (NOW() + INTERVAL  '2 hours 20 minutes')),
('ORD-0010', 'APPT-TODAY-002', 2,  (NOW() + INTERVAL  '5 hours'));

-- ──────────────────────────────────────────────────────────────────────────────
-- ORDER LINES
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS order_lines (
    line_id    VARCHAR(50) PRIMARY KEY,
    order_id   VARCHAR(50) NOT NULL REFERENCES outbound_orders(order_id),
    sku_id     VARCHAR(50) NOT NULL REFERENCES skus(sku_id),
    quantity   INTEGER     NOT NULL,
    picked     BOOLEAN     NOT NULL DEFAULT FALSE
);

INSERT INTO order_lines (line_id, order_id, sku_id, quantity, picked) VALUES
-- Order 0001: dock 1, priority 8
('LINE-0001', 'ORD-0001', 'SKU-A001', 20, FALSE),
('LINE-0002', 'ORD-0001', 'SKU-A002',  5, FALSE),
('LINE-0003', 'ORD-0001', 'SKU-A010', 40, FALSE),
-- Order 0002: dock 1, priority 7
('LINE-0004', 'ORD-0002', 'SKU-A003', 80, FALSE),
('LINE-0005', 'ORD-0002', 'SKU-A004', 60, FALSE),
-- Order 0003: dock 2, priority 5
('LINE-0006', 'ORD-0003', 'SKU-B001', 30, FALSE),
('LINE-0007', 'ORD-0003', 'SKU-B002',  8, FALSE),
('LINE-0008', 'ORD-0003', 'SKU-A005', 25, FALSE),
-- Order 0004: dock 2, priority 6
('LINE-0009', 'ORD-0004', 'SKU-A006', 20, FALSE),
('LINE-0010', 'ORD-0004', 'SKU-B003', 15, FALSE),
-- Order 0005: dock 3, priority 4
('LINE-0011', 'ORD-0005', 'SKU-B004', 50, FALSE),
('LINE-0012', 'ORD-0005', 'SKU-C001',  5, FALSE),
-- Order 0006: dock 3, priority 9 (urgent)
('LINE-0013', 'ORD-0006', 'SKU-A007',  3, FALSE),
('LINE-0014', 'ORD-0006', 'SKU-A008', 10, FALSE),
('LINE-0015', 'ORD-0006', 'SKU-A009',  2, FALSE),
-- Order 0007: dock 4, priority 3
('LINE-0016', 'ORD-0007', 'SKU-B005', 100, FALSE),
('LINE-0017', 'ORD-0007', 'SKU-C002',  10, FALSE),
-- Order 0008: dock 4, priority 5
('LINE-0018', 'ORD-0008', 'SKU-B006',  4, FALSE),
('LINE-0019', 'ORD-0008', 'SKU-B007',  2, FALSE),
-- Order 0009: dock 1, priority 10 (highest)
('LINE-0020', 'ORD-0009', 'SKU-A001', 10, FALSE),
('LINE-0021', 'ORD-0009', 'SKU-A011', 15, FALSE),
('LINE-0022', 'ORD-0009', 'SKU-A012',  8, FALSE),
-- Order 0010: dock 2, priority 2
('LINE-0023', 'ORD-0010', 'SKU-B008', 30, FALSE),
('LINE-0024', 'ORD-0010', 'SKU-B009', 20, FALSE);
