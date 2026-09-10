-- 制药公司核心业务数据库
-- 迁移来源：Benjamindaoson/deepagent_search @ 130e2a233a5ddd75c77985bc8e8032c28c69e3b1

CREATE DATABASE IF NOT EXISTS pharma_db
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;
USE pharma_db;

DROP TABLE IF EXISTS sales_records;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS drugs;

CREATE TABLE drugs (
    drug_id INT PRIMARY KEY AUTO_INCREMENT,
    generic_name VARCHAR(100) NOT NULL,
    brand_name VARCHAR(100),
    approval_number VARCHAR(50),
    specifications VARCHAR(100),
    dosage_form VARCHAR(50),
    manufacturer VARCHAR(100),
    therapeutic_area VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE inventory (
    inventory_id INT PRIMARY KEY AUTO_INCREMENT,
    drug_id INT NOT NULL,
    batch_number VARCHAR(50) NOT NULL,
    quantity_on_hand INT DEFAULT 0,
    warehouse_location VARCHAR(100),
    production_date DATE,
    expiry_date DATE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_inventory_drug FOREIGN KEY (drug_id) REFERENCES drugs(drug_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE sales_records (
    sale_id INT PRIMARY KEY AUTO_INCREMENT,
    drug_id INT NOT NULL,
    sale_date DATE NOT NULL,
    quantity_sold INT NOT NULL,
    unit_price DECIMAL(10, 2),
    total_amount DECIMAL(15, 2),
    customer_name VARCHAR(100),
    region VARCHAR(50),
    sales_rep VARCHAR(50),
    CONSTRAINT fk_sales_drug FOREIGN KEY (drug_id) REFERENCES drugs(drug_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_inventory_drug_id ON inventory(drug_id);
CREATE INDEX idx_sales_drug_id ON sales_records(drug_id);
CREATE INDEX idx_sales_region ON sales_records(region);
CREATE INDEX idx_sales_date ON sales_records(sale_date);

INSERT INTO drugs
(generic_name, brand_name, approval_number, specifications, dosage_form, manufacturer, therapeutic_area, description)
VALUES
('阿莫西林胶囊', '阿莫仙', '国药准字H20051234', '0.25g*24粒/盒', '胶囊剂', '本公司制药', '抗生素', '用于敏感菌所致的呼吸道、泌尿系统、皮肤软组织等感染。'),
('布洛芬缓释胶囊', '芬必得', '国药准字H20010456', '0.3g*20粒/盒', '胶囊剂', '本公司制药', '解热镇痛', '用于缓解轻至中度疼痛，也可用于普通感冒或流感引起的发热。'),
('盐酸二甲双胍片', '格华止', '国药准字H20023370', '0.5g*30片/盒', '片剂', '本公司制药', '糖尿病', '用于2型糖尿病患者的血糖控制。'),
('阿托伐他汀钙片', '立普妥', '国药准字H20051408', '20mg*7片/盒', '片剂', '本公司制药', '心血管', '用于高胆固醇血症和冠心病相关风险控制。'),
('连花清瘟胶囊', '连花清瘟', '国药准字Z20040063', '0.35g*24粒/盒', '胶囊剂', '本公司制药', '中成药/感冒', '清瘟解毒，宣肺泄热，用于流行性感冒相关症状。');

INSERT INTO inventory
(drug_id, batch_number, quantity_on_hand, warehouse_location, production_date, expiry_date)
VALUES
(1, 'AMX-250101-A', 5000, '北京一号库-A区', '2025-01-01', '2027-01-01'),
(1, 'AMX-250615-B', 8000, '北京二号库-B区', '2025-06-15', '2027-06-14'),
(2, 'BLF-250101-A', 3000, '天津一号库-A区', '2025-01-01', '2027-01-01'),
(2, 'BLF-250615-B', 15000, '北京一号库-C区', '2025-06-15', '2027-06-14'),
(3, 'EJSG-250101-A', 4000, '广州一号库-A区', '2025-01-01', '2027-01-01'),
(3, 'EJSG-250615-B', 6000, '深圳一号库-B区', '2025-06-15', '2027-06-14'),
(4, 'ATFT-250101-A', 2000, '成都一号库-A区', '2025-01-01', '2027-01-01'),
(4, 'ATFT-250615-B', 3500, '重庆一号库-B区', '2025-06-15', '2027-06-14'),
(5, 'LHQW-250101-A', 10000, '天津二号库-防疫专区', '2025-01-01', '2027-01-01'),
(5, 'LHQW-250615-B', 50000, '北京二号库-防疫专区', '2025-06-15', '2027-06-14');

INSERT INTO sales_records
(drug_id, sale_date, quantity_sold, unit_price, total_amount, customer_name, region, sales_rep)
VALUES
(1, '2025-02-15', 200, 25.00, 5000.00, '北京朝阳医院', '华北区', '北京朝阳销售部'),
(1, '2025-08-10', 500, 24.50, 12250.00, '天津大药房', '华北区', '天津南开销售分部'),
(2, '2025-01-20', 1000, 15.00, 15000.00, '海王星辰连锁', '华东区', '杭州滨江销售部'),
(2, '2025-12-05', 5000, 15.00, 75000.00, '上海华山医院', '华东区', '上海静安销售总部'),
(3, '2025-03-10', 300, 35.00, 10500.00, '广州中山医院', '华南区', '广州越秀销售部'),
(3, '2025-09-22', 400, 35.00, 14000.00, '深圳人民医院', '华南区', '深圳罗湖销售分部'),
(4, '2025-04-05', 100, 45.00, 4500.00, '成都华西医院', '西南区', '成都武侯销售部'),
(4, '2025-10-18', 150, 45.00, 6750.00, '重庆大药房', '西南区', '重庆渝中销售部'),
(5, '2025-05-12', 3000, 32.00, 96000.00, '武汉同济医院', '华中区', '武汉江汉销售部'),
(5, '2025-11-20', 8000, 31.50, 252000.00, '郑州中心医院', '华中区', '郑州金水销售部');
