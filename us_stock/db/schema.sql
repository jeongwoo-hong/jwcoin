-- US Stock Wealth Builder Supabase Schema
-- 미국 주식 자동매매 시스템 데이터베이스 스키마

-- 1. 거래 기록 테이블
CREATE TABLE IF NOT EXISTS us_stock_trades (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),

    -- 거래 정보
    symbol VARCHAR(10) NOT NULL,
    action VARCHAR(20) NOT NULL,  -- buy, sell, stop_loss, take_profit
    quantity INTEGER NOT NULL,
    price DECIMAL(12, 4) NOT NULL,
    amount DECIMAL(14, 4) NOT NULL,

    -- 주문 정보
    order_id VARCHAR(50),
    order_type VARCHAR(20) DEFAULT 'market',  -- market, limit

    -- 손익
    pnl DECIMAL(12, 4),
    pnl_pct DECIMAL(8, 4),

    -- 손절/익절 설정
    stop_loss DECIMAL(12, 4),
    take_profit DECIMAL(12, 4),

    -- AI 분석 정보
    model VARCHAR(50),
    decision_confidence DECIMAL(5, 4),
    key_reasons JSONB,

    -- 메타데이터
    sector VARCHAR(50),
    notes TEXT
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_us_trades_symbol ON us_stock_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_us_trades_created_at ON us_stock_trades(created_at);
CREATE INDEX IF NOT EXISTS idx_us_trades_action ON us_stock_trades(action);


-- 2. 포트폴리오 스냅샷 테이블
CREATE TABLE IF NOT EXISTS us_stock_portfolio_snapshots (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),

    -- 포트폴리오 요약
    total_value DECIMAL(14, 4) NOT NULL,
    cash DECIMAL(14, 4) NOT NULL,
    cash_ratio DECIMAL(5, 4) NOT NULL,
    invested DECIMAL(14, 4) NOT NULL,

    -- 성과
    daily_pnl DECIMAL(12, 4),
    daily_pnl_pct DECIMAL(8, 4),
    unrealized_pnl DECIMAL(12, 4),
    unrealized_pnl_pct DECIMAL(8, 4),

    -- 포지션 상세
    positions JSONB,
    position_count INTEGER,

    -- 시장 상황
    market_condition JSONB,
    vix DECIMAL(8, 4)
);

CREATE INDEX IF NOT EXISTS idx_us_portfolio_created_at ON us_stock_portfolio_snapshots(created_at);


-- 3. 분석 로그 테이블
CREATE TABLE IF NOT EXISTS us_stock_analysis_logs (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),

    -- 분석 대상
    symbol VARCHAR(10) NOT NULL,
    sector VARCHAR(50),

    -- 점수
    composite_score DECIMAL(6, 2),
    adjusted_score DECIMAL(6, 2),
    confidence DECIMAL(5, 4),

    -- 개별 점수
    technical_score DECIMAL(6, 2),
    fundamental_score DECIMAL(6, 2),
    sentiment_score DECIMAL(6, 2),
    macro_score DECIMAL(6, 2),
    quality_score DECIMAL(6, 2),

    -- 신호
    signal VARCHAR(20),
    decision VARCHAR(20),

    -- 상세 분석
    analysis_detail JSONB,

    -- AI 결정
    ai_decision JSONB,
    model VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_us_analysis_symbol ON us_stock_analysis_logs(symbol);
CREATE INDEX IF NOT EXISTS idx_us_analysis_created_at ON us_stock_analysis_logs(created_at);


-- 4. 알림 테이블
CREATE TABLE IF NOT EXISTS us_stock_alerts (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),

    alert_type VARCHAR(30) NOT NULL,  -- trade, stop_loss, market_risk, system_error
    severity VARCHAR(20) NOT NULL,    -- info, warning, critical

    symbol VARCHAR(10),
    message TEXT NOT NULL,
    details JSONB,

    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_us_alerts_type ON us_stock_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_us_alerts_created_at ON us_stock_alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_us_alerts_is_read ON us_stock_alerts(is_read);


-- 5. 설정 테이블
CREATE TABLE IF NOT EXISTS us_stock_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    description TEXT
);

-- 기본 설정 삽입
INSERT INTO us_stock_settings (key, value, description) VALUES
    ('risk_limits', '{"max_position_pct": 0.05, "max_sector_pct": 0.25, "max_daily_loss_pct": 0.03, "min_cash_ratio": 0.20}', '리스크 한도 설정'),
    ('trading_schedule', '{"pre_market": "22:00", "market_open": "23:35", "market_close": "06:00", "review": "07:00"}', '거래 스케줄'),
    ('watchlist', '["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]', '감시 종목')
ON CONFLICT (key) DO NOTHING;


-- RLS (Row Level Security) 설정
-- 필요시 활성화
-- ALTER TABLE us_stock_trades ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE us_stock_portfolio_snapshots ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE us_stock_analysis_logs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE us_stock_alerts ENABLE ROW LEVEL SECURITY;