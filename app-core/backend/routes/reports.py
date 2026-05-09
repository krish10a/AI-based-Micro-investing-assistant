"""Reports management routes."""

import logging
import uuid
import json
import csv
import io
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status, Response

from models.schemas import (
    ReportSummary,
    ReportSummaryResponse,
    ReportExportRequest,
    ReportExportResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Mock storage for report generation
reports_storage: Dict[str, Dict[str, Any]] = {}


@router.get("/reports/summary", response_model=ReportSummaryResponse)
async def generate_summary_report(user_id: str):
    """
    Generate a summary report for the user.

    Args:
        user_id: User ID

    Returns:
        Comprehensive summary report with portfolio, SIP, and goals data
    """
    try:
        # Import data from other services/routes
        from routes.portfolio import _generate_mock_holdings
        from routes.sips import sips_storage
        from routes.goals import goals_service

        # Get portfolio data
        holdings = _generate_mock_holdings(user_id)
        total_value = sum(h["current_value"] for h in holdings)
        total_invested = sum(h["quantity"] * h["average_cost"] for h in holdings)
        total_gain_loss = total_value - total_invested
        return_percentage = (total_gain_loss / total_invested * 100) if total_invested > 0 else 0

        # Get SIP data
        user_sips = [s for s in sips_storage.values() if s["user_id"] == user_id]
        active_sips = len([s for s in user_sips if s["status"] == "active"])

        # Get goals data
        try:
            goals_summary = goals_service.get_goals_summary()
            total_goals = goals_summary["total_goals"]
            completed_goals = goals_summary["achieved_count"]
        except Exception:
            total_goals = 0
            completed_goals = 0

        # Asset allocation summary
        asset_allocation: Dict[str, float] = {}
        for holding in holdings:
            asset_type = holding["asset_type"]
            if asset_type not in asset_allocation:
                asset_allocation[asset_type] = 0
            asset_allocation[asset_type] += holding["current_value"]

        if total_value > 0:
            asset_allocation = {
                k: round((v / total_value) * 100, 2)
                for k, v in asset_allocation.items()
            }

        # Top holding
        top_holding = None
        if holdings:
            top = max(holdings, key=lambda h: h["current_value"])
            top_holding = top["symbol"]

        # Risk profile based on allocation
        equity_ratio = asset_allocation.get("equity", 0)
        if equity_ratio > 70:
            risk_profile = "Aggressive"
        elif equity_ratio > 40:
            risk_profile = "Moderate"
        else:
            risk_profile = "Conservative"

        summary = ReportSummary(
            user_id=user_id,
            report_date=datetime.utcnow().isoformat(),
            total_invested=round(total_invested, 2),
            current_value=round(total_value, 2),
            total_gain_loss=round(total_gain_loss, 2),
            return_percentage=round(return_percentage, 2),
            active_sips=active_sips,
            total_goals=total_goals,
            completed_goals=completed_goals,
            top_holding=top_holding,
            asset_allocation_summary=asset_allocation,
            risk_profile=risk_profile,
            financial_health_score=75.0,  # Mock value
        )

        return ReportSummaryResponse(
            summary=summary,
            generated_at=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        logger.error(f"Failed to generate summary report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate summary report",
        )


@router.get("/reports/tax/{year}")
async def get_tax_report(year: int, user_id: str = "default_user"):
    """
    Get tax report for a specific year.
    """
    try:
        from routes.transactions import transactions_storage
        user_transactions = [
            t
            for t in transactions_storage.values()
            if t["user_id"] == user_id
            and t["type"] in ["investment", "withdrawal", "dividend"]
        ]
        
        # Mock calculation
        capital_gains_st = 0
        capital_gains_lt = 0
        dividend_income = 0
        
        for t in user_transactions:
            if t["type"] == "withdrawal":
                capital_gains_st += t["amount"] * 0.1  # Mock calculation
            elif t["type"] == "dividend":
                dividend_income += t["amount"]
                
        return {
            "year": year,
            "short_term_capital_gains": round(capital_gains_st, 2),
            "long_term_capital_gains": round(capital_gains_lt, 2),
            "dividend_income": round(dividend_income, 2),
            "tax_saving_investments": 150000, # Mock ELSS limit
            "estimated_tax_liability": round((capital_gains_st * 0.15) + (capital_gains_lt * 0.1), 2)
        }
    except Exception as e:
        logger.error(f"Failed to generate tax report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate tax report",
        )


@router.get("/reports/insights")
async def get_insights(user_id: str = "default_user"):
    """
    Get AI-generated insights.
    """
    return [
        {
            "insight": "Your portfolio is heavily skewed towards large-cap equities. Consider diversifying into mid-cap or debt instruments.",
            "category": "risk",
            "impact": "high"
        },
        {
            "insight": "You have a consistent investment streak! Your SIPs are performing 12% better than the benchmark.",
            "category": "performance",
            "impact": "medium"
        },
        {
            "insight": "Tax-saving season is approaching. You have ₹50,000 left under section 80C.",
            "category": "opportunity",
            "impact": "high"
        }
    ]


@router.post("/reports/export", response_model=ReportExportResponse)
async def export_report(
    export_request: ReportExportRequest,
    user_id: str = "default_user",
):
    """
    Export reports to various formats (JSON, CSV, PDF).

    Args:
        report_type: Type of report (summary, transactions, portfolio, tax)
        format: Output format (json, csv, pdf)
        start_date: Start date for date range reports
        end_date: End date for date range reports
        include_charts: Include chart data in export

    Returns:
        Export result with file URL or data
    """
    try:
        report_id = str(uuid.uuid4())

        # Import data
        from routes.portfolio import _generate_mock_holdings
        from routes.sips import sips_storage
        from routes.transactions import transactions_storage
        from routes.goals import goals_service

        now = datetime.utcnow().isoformat()

        # Generate report data based on type
        report_data: Dict[str, Any] = {
            "report_id": report_id,
            "user_id": user_id,
            "report_type": export_request.report_type,
            "generated_at": now,
        }

        if export_request.report_type == "summary":
            holdings = _generate_mock_holdings(user_id)
            total_value = sum(h["current_value"] for h in holdings)
            total_invested = sum(h["quantity"] * h["average_cost"] for h in holdings)

            report_data.update(
                {
                    "total_invested": total_invested,
                    "current_value": total_value,
                    "total_gain_loss": total_value - total_invested,
                    "holdings_count": len(holdings),
                }
            )

        elif export_request.report_type == "transactions":
            user_transactions = [
                t for t in transactions_storage.values() if t["user_id"] == user_id
            ]
            report_data["transactions"] = user_transactions
            report_data["transaction_count"] = len(user_transactions)

        elif export_request.report_type == "portfolio":
            holdings = _generate_mock_holdings(user_id)
            report_data["holdings"] = holdings
            report_data["total_value"] = sum(h["current_value"] for h in holdings)
            report_data["asset_allocation"] = _calculate_asset_allocation(holdings)

        elif export_request.report_type == "tax":
            # Generate tax-related data
            user_transactions = [
                t
                for t in transactions_storage.values()
                if t["user_id"] == user_id
                and t["type"] in ["investment", "withdrawal"]
            ]
            report_data["taxable_transactions"] = user_transactions
            report_data["fiscal_year"] = datetime.utcnow().strftime("%Y-%Y+1")

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown report type: {export_request.report_type}",
            )

        # Add chart data if requested
        if export_request.include_charts:
            report_data["charts"] = {
                "asset_allocation": _generate_mock_chart_data(),
                "performance_history": _generate_mock_performance_chart(),
            }

        # Store report
        reports_storage[report_id] = report_data

        # Export based on format
        file_url = f"/api/v1/reports/download/{report_id}"
        file_size = len(json.dumps(report_data))

        if export_request.format == "json":
            return ReportExportResponse(
                success=True,
                file_url=file_url,
                file_size=file_size,
                format="json",
                message="Report exported successfully as JSON",
            )

        elif export_request.format == "csv":
            # Generate CSV
            csv_buffer = io.StringIO()
            if report_data.get("transactions"):
                writer = csv.DictWriter(csv_buffer, fieldnames=report_data["transactions"][0].keys())
                writer.writeheader()
                writer.writerows(report_data["transactions"])
            elif report_data.get("holdings"):
                writer = csv.DictWriter(csv_buffer, fieldnames=report_data["holdings"][0].keys())
                writer.writeheader()
                writer.writerows(report_data["holdings"])
            else:
                writer = csv.DictWriter(csv_buffer, fieldnames=report_data.keys())
                writer.writeheader()
                writer.writerow(report_data)

            return ReportExportResponse(
                success=True,
                file_url=f"{file_url}.csv",
                file_size=len(csv_buffer.getvalue()),
                format="csv",
                message="Report exported successfully as CSV",
            )

        elif export_request.format == "pdf":
            # For PDF, we would need a PDF library like reportlab or weasyprint
            # Return a placeholder response
            return ReportExportResponse(
                success=True,
                file_url=f"{file_url}.pdf",
                file_size=file_size * 2,  # Estimated PDF size
                format="pdf",
                message="PDF export generated (mock - requires PDF library for production)",
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported export format: {export_request.format}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not export report",
        )


@router.get("/reports/download/{report_id}")
async def download_report(report_id: str, format: str = "json"):
    """
    Download a generated report.

    Args:
        report_id: Report ID
        format: File format (json, csv, pdf)

    Returns:
        File download
    """
    try:
        report = reports_storage.get(report_id)

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID '{report_id}' not found",
            )

        if format == "json":
            return Response(
                content=json.dumps(report, indent=2),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=report_{report_id}.json"},
            )

        elif format == "csv":
            csv_buffer = io.StringIO()
            if report.get("transactions"):
                writer = csv.DictWriter(csv_buffer, fieldnames=report["transactions"][0].keys())
                writer.writeheader()
                writer.writerows(report["transactions"])
            elif report.get("holdings"):
                writer = csv.DictWriter(csv_buffer, fieldnames=report["holdings"][0].keys())
                writer.writeheader()
                writer.writerows(report["holdings"])
            else:
                writer = csv.DictWriter(csv_buffer, fieldnames=report.keys())
                writer.writeheader()
                writer.writerow(report)

            return Response(
                content=csv_buffer.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=report_{report_id}.csv"},
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format: {format}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not download report",
        )


def _calculate_asset_allocation(holdings: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate asset allocation percentages."""
    allocation: Dict[str, float] = {}
    total_value = sum(h["current_value"] for h in holdings)

    for holding in holdings:
        asset_type = holding["asset_type"]
        if asset_type not in allocation:
            allocation[asset_type] = 0
        allocation[asset_type] += holding["current_value"]

    if total_value > 0:
        allocation = {k: round((v / total_value) * 100, 2) for k, v in allocation.items()}

    return allocation


def _generate_mock_chart_data() -> List[Dict[str, Any]]:
    """Generate mock chart data for asset allocation."""
    return [
        {"label": "Equity", "value": 60, "color": "#4ade80"},
        {"label": "Debt", "value": 20, "color": "#60a5fa"},
        {"label": "Gold", "value": 10, "color": "#fbbf24"},
        {"label": "Cash", "value": 10, "color": "#94a3b8"},
    ]


def _generate_mock_performance_chart() -> List[Dict[str, float]]:
    """Generate mock performance chart data."""
    return [
        {"date": "2025-01", "value": 100000},
        {"date": "2025-02", "value": 102500},
        {"date": "2025-03", "value": 101800},
        {"date": "2025-04", "value": 105000},
        {"date": "2025-05", "value": 108500},
    ]
