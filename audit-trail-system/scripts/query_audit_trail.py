#!/usr/bin/env python3
"""
Query Audit Trail Script

Helper script to query and analyze audit trail data from the command line.
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.session import SessionLocal
from backend.models.audit_log import AuditLog, AuditEventType, AuditSeverity
from sqlalchemy import desc, func


def query_by_case(case_id: str, limit: int = 100):
    """Query audit logs by case ID"""
    db = SessionLocal()
    try:
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.case_id == case_id)
            .order_by(desc(AuditLog.event_timestamp))
            .limit(limit)
            .all()
        )
        
        print(f"\nFound {len(logs)} audit entries for case {case_id}:")
        print("=" * 80)
        
        for log in logs:
            print(f"\n[{log.event_timestamp}] {log.event_type.value}")
            print(f"  User: {log.user_id} ({log.user_email})")
            print(f"  Severity: {log.severity.value}")
            if log.notes:
                print(f"  Notes: {log.notes}")
            if log.error_occurred:
                print(f"  ERROR: {log.error_message}")
        
        return logs
    finally:
        db.close()


def query_by_user(user_id: str, days: int = 30, limit: int = 100):
    """Query audit logs by user ID"""
    db = SessionLocal()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.user_id == user_id,
                AuditLog.event_timestamp >= start_date
            )
            .order_by(desc(AuditLog.event_timestamp))
            .limit(limit)
            .all()
        )
        
        print(f"\nFound {len(logs)} audit entries for user {user_id} (last {days} days):")
        print("=" * 80)
        
        for log in logs:
            print(f"\n[{log.event_timestamp}] {log.event_type.value}")
            print(f"  Case: {log.case_id}")
            print(f"  Severity: {log.severity.value}")
            if log.notes:
                print(f"  Notes: {log.notes}")
        
        return logs
    finally:
        db.close()


def query_sar_trail(case_id: str):
    """Query SAR-specific audit trail"""
    db = SessionLocal()
    try:
        logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.case_id == case_id,
                AuditLog.event_type.in_([
                    AuditEventType.SAR_GENERATION_STARTED,
                    AuditEventType.SAR_REASONING_GENERATED,
                    AuditEventType.SAR_REPORT_GENERATED,
                    AuditEventType.SAR_REPORT_REVIEWED,
                    AuditEventType.SAR_REPORT_SUBMITTED,
                    AuditEventType.SAR_GENERATION_FAILED,
                ])
            )
            .order_by(AuditLog.event_timestamp.asc())
            .all()
        )
        
        print(f"\nSAR Audit Trail for case {case_id}:")
        print("=" * 80)
        
        for i, log in enumerate(logs, 1):
            print(f"\n{i}. [{log.event_timestamp}] {log.event_type.value}")
            print(f"   User: {log.user_id}")
            
            if log.event_type == AuditEventType.SAR_REASONING_GENERATED:
                if log.sar_reasoning:
                    print(f"   Reasoning: {log.sar_reasoning[:100]}...")
                if log.processing_duration_ms:
                    print(f"   Processing time: {log.processing_duration_ms}ms")
            
            elif log.event_type == AuditEventType.SAR_REPORT_GENERATED:
                if log.sar_report_metadata:
                    print(f"   Metadata: {json.dumps(log.sar_report_metadata, indent=4)}")
            
            elif log.event_type == AuditEventType.SAR_REPORT_REVIEWED:
                if log.changes_made:
                    decision = log.changes_made.get('review_decision')
                    print(f"   Decision: {decision}")
            
            elif log.event_type == AuditEventType.SAR_REPORT_SUBMITTED:
                print(f"   Filing Number: {log.sar_filing_number}")
            
            elif log.event_type == AuditEventType.SAR_GENERATION_FAILED:
                print(f"   ERROR: {log.error_message}")
        
        return logs
    finally:
        db.close()


def query_by_filing_number(filing_number: str):
    """Query audit log by SAR filing number"""
    db = SessionLocal()
    try:
        log = (
            db.query(AuditLog)
            .filter(AuditLog.sar_filing_number == filing_number)
            .first()
        )
        
        if log:
            print(f"\nFound SAR filing: {filing_number}")
            print("=" * 80)
            print(f"Case ID: {log.case_id}")
            print(f"User: {log.user_id} ({log.user_email})")
            print(f"Timestamp: {log.event_timestamp}")
            print(f"Severity: {log.severity.value}")
            if log.sar_report_metadata:
                print(f"\nMetadata:")
                print(json.dumps(log.sar_report_metadata, indent=2))
        else:
            print(f"\nNo SAR filing found with number: {filing_number}")
        
        return log
    finally:
        db.close()


def get_statistics(days: int = 30):
    """Get audit trail statistics"""
    db = SessionLocal()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Total events
        total = db.query(AuditLog).filter(
            AuditLog.event_timestamp >= start_date
        ).count()
        
        # Events by type
        by_type = db.query(
            AuditLog.event_type,
            func.count(AuditLog.id)
        ).filter(
            AuditLog.event_timestamp >= start_date
        ).group_by(AuditLog.event_type).all()
        
        # Events by severity
        by_severity = db.query(
            AuditLog.severity,
            func.count(AuditLog.id)
        ).filter(
            AuditLog.event_timestamp >= start_date
        ).group_by(AuditLog.severity).all()
        
        # Errors
        errors = db.query(AuditLog).filter(
            AuditLog.event_timestamp >= start_date,
            AuditLog.error_occurred == True
        ).count()
        
        # SAR statistics
        sars_generated = db.query(AuditLog).filter(
            AuditLog.event_timestamp >= start_date,
            AuditLog.event_type == AuditEventType.SAR_REPORT_GENERATED
        ).count()
        
        sars_submitted = db.query(AuditLog).filter(
            AuditLog.event_timestamp >= start_date,
            AuditLog.event_type == AuditEventType.SAR_REPORT_SUBMITTED
        ).count()
        
        # Print statistics
        print(f"\nAudit Trail Statistics (last {days} days)")
        print("=" * 80)
        print(f"Total Events: {total}")
        print(f"Errors: {errors}")
        print(f"SARs Generated: {sars_generated}")
        print(f"SARs Submitted: {sars_submitted}")
        
        print("\nEvents by Type:")
        for event_type, count in by_type:
            print(f"  {event_type.value}: {count}")
        
        print("\nEvents by Severity:")
        for severity, count in by_severity:
            print(f"  {severity.value}: {count}")
        
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Query Audit Trail Data"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Case query
    case_parser = subparsers.add_parser('case', help='Query by case ID')
    case_parser.add_argument('case_id', help='Case ID to query')
    case_parser.add_argument('--limit', type=int, default=100, help='Max results')
    
    # User query
    user_parser = subparsers.add_parser('user', help='Query by user ID')
    user_parser.add_argument('user_id', help='User ID to query')
    user_parser.add_argument('--days', type=int, default=30, help='Days to look back')
    user_parser.add_argument('--limit', type=int, default=100, help='Max results')
    
    # SAR trail
    sar_parser = subparsers.add_parser('sar', help='Query SAR audit trail')
    sar_parser.add_argument('case_id', help='Case ID to query')
    
    # Filing number
    filing_parser = subparsers.add_parser('filing', help='Query by SAR filing number')
    filing_parser.add_argument('filing_number', help='SAR filing number')
    
    # Statistics
    stats_parser = subparsers.add_parser('stats', help='Get statistics')
    stats_parser.add_argument('--days', type=int, default=30, help='Days to analyze')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("\n" + "=" * 80)
    print("Audit Trail Query Tool")
    print("=" * 80)
    
    try:
        if args.command == 'case':
            query_by_case(args.case_id, args.limit)
        elif args.command == 'user':
            query_by_user(args.user_id, args.days, args.limit)
        elif args.command == 'sar':
            query_sar_trail(args.case_id)
        elif args.command == 'filing':
            query_by_filing_number(args.filing_number)
        elif args.command == 'stats':
            get_statistics(args.days)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
