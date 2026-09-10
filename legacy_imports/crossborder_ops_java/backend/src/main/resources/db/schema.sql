DROP TABLE IF EXISTS cb_listing;
DROP TABLE IF EXISTS cb_review;
DROP TABLE IF EXISTS cb_ad_daily_report;
DROP TABLE IF EXISTS cb_ad_campaign;
DROP TABLE IF EXISTS cb_refund;
DROP TABLE IF EXISTS cb_order;
DROP TABLE IF EXISTS cb_sku;
DROP TABLE IF EXISTS cb_operator;
DROP TABLE IF EXISTS cb_store;

CREATE TABLE cb_store (
    id BIGINT NOT NULL,
    name VARCHAR(80) NOT NULL,
    platform VARCHAR(40) NOT NULL,
    marketplace VARCHAR(40) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    manager_operator_id BIGINT DEFAULT NULL,
    PRIMARY KEY (id),
    KEY idx_cb_store_marketplace (marketplace)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='cross-border store';

CREATE TABLE cb_operator (
    id BIGINT NOT NULL,
    name VARCHAR(60) NOT NULL,
    role VARCHAR(40) NOT NULL,
    store_id BIGINT DEFAULT NULL,
    email VARCHAR(120) DEFAULT NULL,
    PRIMARY KEY (id),
    KEY idx_cb_operator_store (store_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='operations user';

CREATE TABLE cb_sku (
    id BIGINT NOT NULL,
    store_id BIGINT NOT NULL,
    sku_code VARCHAR(60) NOT NULL,
    title VARCHAR(160) NOT NULL,
    category VARCHAR(60) NOT NULL,
    target_marketplace VARCHAR(40) NOT NULL,
    unit_cost DECIMAL(12,2) NOT NULL,
    status VARCHAR(30) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_cb_sku_code (sku_code),
    KEY idx_cb_sku_store (store_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='cross-border sku';

CREATE TABLE cb_order (
    id BIGINT NOT NULL,
    order_no VARCHAR(60) NOT NULL,
    store_id BIGINT NOT NULL,
    sku_id BIGINT NOT NULL,
    country VARCHAR(40) NOT NULL,
    quantity INT NOT NULL,
    gross_amount DECIMAL(14,2) NOT NULL,
    net_amount DECIMAL(14,2) NOT NULL,
    cost_amount DECIMAL(14,2) NOT NULL,
    profit_amount DECIMAL(14,2) NOT NULL,
    status VARCHAR(30) NOT NULL,
    order_date DATE NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_cb_order_no (order_no),
    KEY idx_cb_order_store_date (store_id, order_date),
    KEY idx_cb_order_sku_date (sku_id, order_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='cross-border order';

CREATE TABLE cb_refund (
    id BIGINT NOT NULL,
    order_id BIGINT NOT NULL,
    store_id BIGINT NOT NULL,
    sku_id BIGINT NOT NULL,
    reason VARCHAR(120) NOT NULL,
    refund_amount DECIMAL(14,2) NOT NULL,
    refund_date DATE NOT NULL,
    PRIMARY KEY (id),
    KEY idx_cb_refund_store_date (store_id, refund_date),
    KEY idx_cb_refund_sku_date (sku_id, refund_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='refund record';

CREATE TABLE cb_ad_campaign (
    id BIGINT NOT NULL,
    store_id BIGINT NOT NULL,
    sku_id BIGINT NOT NULL,
    campaign_name VARCHAR(120) NOT NULL,
    channel VARCHAR(40) NOT NULL,
    status VARCHAR(30) NOT NULL,
    PRIMARY KEY (id),
    KEY idx_cb_campaign_store (store_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ad campaign';

CREATE TABLE cb_ad_daily_report (
    id BIGINT NOT NULL,
    campaign_id BIGINT NOT NULL,
    store_id BIGINT NOT NULL,
    sku_id BIGINT NOT NULL,
    report_date DATE NOT NULL,
    spend DECIMAL(14,2) NOT NULL,
    sales_amount DECIMAL(14,2) NOT NULL,
    clicks INT NOT NULL,
    orders INT NOT NULL,
    PRIMARY KEY (id),
    KEY idx_cb_ad_store_date (store_id, report_date),
    KEY idx_cb_ad_campaign_date (campaign_id, report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ad daily report';

CREATE TABLE cb_review (
    id BIGINT NOT NULL,
    store_id BIGINT NOT NULL,
    sku_id BIGINT NOT NULL,
    rating INT NOT NULL,
    content VARCHAR(600) NOT NULL,
    locale VARCHAR(20) NOT NULL,
    review_date DATE NOT NULL,
    PRIMARY KEY (id),
    KEY idx_cb_review_store_date (store_id, review_date),
    KEY idx_cb_review_sku_date (sku_id, review_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='product review';

CREATE TABLE cb_listing (
    id BIGINT NOT NULL,
    sku_id BIGINT NOT NULL,
    marketplace VARCHAR(40) NOT NULL,
    locale VARCHAR(20) NOT NULL,
    title VARCHAR(220) NOT NULL,
    bullets VARCHAR(1200) NOT NULL,
    keywords VARCHAR(300) NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_cb_listing_sku (sku_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='listing draft';

CREATE TABLE IF NOT EXISTS sa_chat_memory (
    id BIGINT NOT NULL AUTO_INCREMENT,
    session_id VARCHAR(100) NOT NULL,
    messages LONGTEXT NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='chat memory';
