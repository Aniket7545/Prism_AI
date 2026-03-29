import sqlite3
import json
from datetime import datetime
import os
from config import Config

class AuditDatabase:
    def __init__(self):
        os.makedirs(os.path.dirname(Config.AUDIT_DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(Config.AUDIT_DB_PATH, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Audit logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                session_id TEXT,
                agent_name TEXT,
                action TEXT,
                input_summary TEXT,
                output_summary TEXT,
                status TEXT,
                details TEXT
            )
        """)
        
        # Content sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                created_at TEXT,
                status TEXT,
                topic TEXT,
                channel TEXT,
                region TEXT,
                content_type TEXT,
                created_by TEXT
            )
        """)
        
        # Content assets (versions and drafts)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                version INTEGER,
                created_at TEXT,
                content_type TEXT,
                raw_content TEXT,
                draft_content TEXT,
                localized_content TEXT,
                agent_source TEXT,
                metadata TEXT
            )
        """)
        
        # Compliance reports
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                version INTEGER,
                created_at TEXT,
                passed INTEGER,
                risk_level TEXT,
                issues TEXT,
                fixes TEXT,
                details TEXT
            )
        """)
        
        # Performance metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                metric_name TEXT,
                metric_value REAL,
                timestamp TEXT,
                details TEXT
            )
        """)
        
        # Content feedback
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                version INTEGER,
                feedback_type TEXT,
                feedback_text TEXT,
                severity TEXT,
                created_at TEXT,
                created_by TEXT
            )
        """)
        
        # Content templates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT,
                template_type TEXT,
                category TEXT,
                content TEXT,
                brand_guidelines TEXT,
                created_at TEXT,
                created_by TEXT,
                is_active INTEGER
            )
        """)
        
        # Channel configurations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channel_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_name TEXT,
                api_endpoint TEXT,
                credentials TEXT,
                max_content_length INTEGER,
                required_fields TEXT,
                formatting_rules TEXT,
                is_active INTEGER
            )
        """)
        
        # Engagement metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS engagement_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                channel TEXT,
                published_content_id TEXT,
                views INTEGER,
                engagements INTEGER,
                shares INTEGER,
                click_rate REAL,
                sentiment_score REAL,
                collected_at TEXT
            )
        """)
        
        self.conn.commit()

    def log_event(self, session_id, agent, action, input_sum, output_sum, status, details=None):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (timestamp, session_id, agent_name, action, input_summary, output_summary, status, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), session_id, agent, action, input_sum, output_sum, status, json.dumps(details) if details else None))
        self.conn.commit()

    def get_session_logs(self, session_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM audit_logs WHERE session_id = ?", (session_id,))
        return cursor.fetchall()
    
    def create_session(self, session_id, topic, channel, region, content_type="article"):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO content_sessions (session_id, created_at, status, topic, channel, region, content_type, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, datetime.now().isoformat(), "started", topic, channel, region, content_type, "system"))
        self.conn.commit()
    
    def save_content_asset(self, session_id, version, content_type, raw_content, draft_content, agent_source):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO content_assets (session_id, version, created_at, content_type, raw_content, draft_content, agent_source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, version, datetime.now().isoformat(), content_type, raw_content, draft_content, agent_source))
        self.conn.commit()
    
    def save_compliance_report(self, session_id, version, passed, risk_level, issues, fixes, details=None):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO compliance_reports (session_id, version, created_at, passed, risk_level, issues, fixes, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, version, datetime.now().isoformat(), 1 if passed else 0, risk_level, json.dumps(issues), json.dumps(fixes), json.dumps(details)))
        self.conn.commit()
    
    def log_metric(self, session_id, metric_name, metric_value, details=None):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO performance_metrics (session_id, metric_name, metric_value, timestamp, details)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, metric_name, metric_value, datetime.now().isoformat(), json.dumps(details)))
        self.conn.commit()
    
    def add_feedback(self, session_id, version, feedback_type, feedback_text, severity="medium"):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO content_feedback (session_id, version, feedback_type, feedback_text, severity, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, version, feedback_type, feedback_text, severity, datetime.now().isoformat(), "human"))
        self.conn.commit()
    
    def get_session_metrics(self, session_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT metric_name, metric_value FROM performance_metrics WHERE session_id = ?", (session_id,))
        return {row[0]: row[1] for row in cursor.fetchall()}
    
    def get_session_content(self, session_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT version, content_type, draft_content, created_at FROM content_assets WHERE session_id = ? ORDER BY version DESC", (session_id,))
        return cursor.fetchall()

audit_db = AuditDatabase()