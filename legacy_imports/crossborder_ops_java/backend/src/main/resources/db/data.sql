INSERT INTO cb_store (id, name, platform, marketplace, currency, manager_operator_id) VALUES
(1, 'Amazon US Store', 'Amazon', 'US', 'USD', 2),
(2, 'TikTok UK Store', 'TikTok Shop', 'UK', 'GBP', 4),
(3, 'Amazon DE Store', 'Amazon', 'DE', 'EUR', 6);

INSERT INTO cb_operator (id, name, role, store_id, email) VALUES
(1, 'Olivia Chen', 'OPERATOR', 1, 'olivia.ops@example.com'),
(2, 'Mia Zhang', 'STORE_MANAGER', 1, 'mia.manager@example.com'),
(3, 'Alex Wang', 'OPERATIONS_DIRECTOR', NULL, 'alex.director@example.com'),
(4, 'Noah Liu', 'STORE_MANAGER', 2, 'noah.uk@example.com'),
(5, 'Emma Zhao', 'OPERATOR', 2, 'emma.uk@example.com'),
(6, 'Leon Sun', 'STORE_MANAGER', 3, 'leon.de@example.com');

INSERT INTO cb_sku (id, store_id, sku_code, title, category, target_marketplace, unit_cost, status) VALUES
(1, 1, 'EB-US-1001', 'Wireless Noise Cancelling Earbuds', 'Electronics', 'Amazon US', 18.50, 'ACTIVE'),
(2, 1, 'YM-US-2001', 'Non-slip Yoga Mat with Carry Strap', 'Sports', 'Amazon US', 9.80, 'ACTIVE'),
(3, 1, 'BK-US-3001', 'Kids STEM Building Blocks 180 PCS', 'Toys', 'Amazon US', 11.20, 'ACTIVE'),
(4, 2, 'HL-UK-1001', 'LED Desk Lamp with USB-C Charging', 'Home', 'TikTok Shop UK', 7.30, 'ACTIVE'),
(5, 2, 'BT-UK-2001', 'Travel Toiletry Bag Waterproof', 'Travel', 'TikTok Shop UK', 4.20, 'ACTIVE'),
(6, 3, 'KT-DE-1001', 'Stainless Steel Lunch Box Set', 'Kitchen', 'Amazon DE', 8.60, 'ACTIVE'),
(7, 3, 'CL-DE-2001', 'Pet Cooling Mat Summer Edition', 'Pet Supplies', 'Amazon DE', 6.40, 'ACTIVE');

INSERT INTO cb_order (id, order_no, store_id, sku_id, country, quantity, gross_amount, net_amount, cost_amount, profit_amount, status, order_date) VALUES
(1, 'CB-001', 1, 1, 'US', 80, 3999.20, 3550.00, 1480.00, 2070.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 175 DAY)),
(2, 'CB-002', 1, 2, 'US', 120, 2998.80, 2620.00, 1176.00, 1444.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 150 DAY)),
(3, 'CB-003', 1, 3, 'US', 60, 2699.40, 2380.00, 672.00, 1708.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 122 DAY)),
(4, 'CB-004', 2, 4, 'GB', 90, 2249.10, 1960.00, 657.00, 1303.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 118 DAY)),
(5, 'CB-005', 2, 5, 'GB', 220, 3297.80, 2875.00, 924.00, 1951.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 94 DAY)),
(6, 'CB-006', 3, 6, 'DE', 110, 3628.90, 3100.00, 946.00, 2154.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 86 DAY)),
(7, 'CB-007', 3, 7, 'DE', 100, 2499.00, 2130.00, 640.00, 1490.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 75 DAY)),
(8, 'CB-008', 1, 1, 'US', 150, 7498.50, 6550.00, 2775.00, 3775.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 62 DAY)),
(9, 'CB-009', 1, 3, 'US', 95, 4274.05, 3690.00, 1064.00, 2626.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 52 DAY)),
(10, 'CB-010', 2, 4, 'GB', 140, 3498.60, 3040.00, 1022.00, 2018.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 46 DAY)),
(11, 'CB-011', 2, 5, 'GB', 260, 3897.40, 3380.00, 1092.00, 2288.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 36 DAY)),
(12, 'CB-012', 3, 6, 'DE', 150, 4948.50, 4210.00, 1290.00, 2920.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 31 DAY)),
(13, 'CB-013', 1, 1, 'US', 180, 8998.20, 7860.00, 3330.00, 4530.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 24 DAY)),
(14, 'CB-014', 1, 2, 'US', 75, 1874.25, 1620.00, 735.00, 885.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 19 DAY)),
(15, 'CB-015', 2, 4, 'GB', 180, 4498.20, 3890.00, 1314.00, 2576.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 13 DAY)),
(16, 'CB-016', 2, 5, 'GB', 320, 4796.80, 4140.00, 1344.00, 2796.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 10 DAY)),
(17, 'CB-017', 3, 6, 'DE', 180, 5938.20, 5000.00, 1548.00, 3452.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 8 DAY)),
(18, 'CB-018', 3, 7, 'DE', 210, 5247.90, 4495.00, 1344.00, 3151.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 5 DAY)),
(19, 'CB-019', 1, 3, 'US', 140, 6298.60, 5380.00, 1568.00, 3812.00, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 3 DAY)),
(20, 'CB-020', 1, 1, 'US', 65, 3249.35, 2800.00, 1202.50, 1597.50, 'COMPLETED', DATE_SUB(CURDATE(), INTERVAL 1 DAY));

INSERT INTO cb_refund (id, order_id, store_id, sku_id, reason, refund_amount, refund_date) VALUES
(1, 8, 1, 1, 'battery drains fast', 219.00, DATE_SUB(CURDATE(), INTERVAL 58 DAY)),
(2, 13, 1, 1, 'left earbud not charging', 249.00, DATE_SUB(CURDATE(), INTERVAL 21 DAY)),
(3, 20, 1, 1, 'noise cancelling weaker than description', 199.00, DATE_SUB(CURDATE(), INTERVAL 1 DAY)),
(4, 14, 1, 2, 'mat is thinner than expected', 79.00, DATE_SUB(CURDATE(), INTERVAL 18 DAY)),
(5, 15, 2, 4, 'damaged package and lamp flicker', 129.00, DATE_SUB(CURDATE(), INTERVAL 12 DAY)),
(6, 17, 3, 6, 'box dented during shipping', 109.00, DATE_SUB(CURDATE(), INTERVAL 7 DAY));

INSERT INTO cb_ad_campaign (id, store_id, sku_id, campaign_name, channel, status) VALUES
(1, 1, 1, 'US Earbuds Prime Search', 'Amazon Ads', 'ACTIVE'),
(2, 1, 3, 'STEM Toy Broad Match', 'Amazon Ads', 'ACTIVE'),
(3, 2, 4, 'UK Desk Lamp Creator Boost', 'TikTok Ads', 'ACTIVE'),
(4, 2, 5, 'Travel Bag Spark Ads', 'TikTok Ads', 'ACTIVE'),
(5, 3, 6, 'DE Lunch Box Sponsored', 'Amazon Ads', 'ACTIVE');

INSERT INTO cb_ad_daily_report (id, campaign_id, store_id, sku_id, report_date, spend, sales_amount, clicks, orders) VALUES
(1, 1, 1, 1, DATE_SUB(CURDATE(), INTERVAL 30 DAY), 680.00, 1540.00, 1200, 32),
(2, 1, 1, 1, DATE_SUB(CURDATE(), INTERVAL 20 DAY), 790.00, 1600.00, 1320, 35),
(3, 1, 1, 1, DATE_SUB(CURDATE(), INTERVAL 10 DAY), 910.00, 1510.00, 1450, 31),
(4, 2, 1, 3, DATE_SUB(CURDATE(), INTERVAL 25 DAY), 360.00, 1820.00, 820, 41),
(5, 2, 1, 3, DATE_SUB(CURDATE(), INTERVAL 8 DAY), 410.00, 2100.00, 870, 47),
(6, 3, 2, 4, DATE_SUB(CURDATE(), INTERVAL 21 DAY), 520.00, 1680.00, 980, 39),
(7, 3, 2, 4, DATE_SUB(CURDATE(), INTERVAL 6 DAY), 630.00, 1710.00, 1100, 40),
(8, 4, 2, 5, DATE_SUB(CURDATE(), INTERVAL 15 DAY), 290.00, 1490.00, 760, 56),
(9, 5, 3, 6, DATE_SUB(CURDATE(), INTERVAL 12 DAY), 440.00, 2400.00, 700, 53),
(10, 5, 3, 6, DATE_SUB(CURDATE(), INTERVAL 4 DAY), 510.00, 2800.00, 780, 62);

INSERT INTO cb_review (id, store_id, sku_id, rating, content, locale, review_date) VALUES
(1, 1, 1, 2, 'Battery drains fast and the left earbud stopped charging after one week.', 'en-US', DATE_SUB(CURDATE(), INTERVAL 20 DAY)),
(2, 1, 1, 3, 'Noise cancelling is weaker than the product description.', 'en-US', DATE_SUB(CURDATE(), INTERVAL 8 DAY)),
(3, 1, 2, 3, 'The mat is smaller and thinner than the pictures suggest.', 'en-US', DATE_SUB(CURDATE(), INTERVAL 17 DAY)),
(4, 2, 4, 2, 'Package arrived damaged and delivery was late.', 'en-GB', DATE_SUB(CURDATE(), INTERVAL 11 DAY)),
(5, 2, 5, 3, 'Good bag but the zipper quality feels cheap.', 'en-GB', DATE_SUB(CURDATE(), INTERVAL 9 DAY)),
(6, 3, 6, 3, 'Box was damaged during shipping, product is fine.', 'de-DE', DATE_SUB(CURDATE(), INTERVAL 6 DAY));

INSERT INTO cb_listing (id, sku_id, marketplace, locale, title, bullets, keywords, updated_at) VALUES
(1, 1, 'Amazon US', 'en-US', 'Wireless Noise Cancelling Earbuds with Charging Case', 'Noise reduction;Long battery;Comfort fit;USB-C case;Clear calls', 'wireless earbuds,noise cancelling,bluetooth earbuds', NOW()),
(2, 4, 'TikTok Shop UK', 'en-GB', 'LED Desk Lamp with USB-C Charging Port', 'Adjustable light;USB-C charging;Compact desk fit;Eye care;Modern design', 'desk lamp,usb c lamp,study light', NOW());
