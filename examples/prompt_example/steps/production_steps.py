"""
Production Deployment Steps

This module demonstrates ZenML's production-ready prompt deployment capabilities:
- Automated deployment of best-performing prompts
- Real-time monitoring and alerting
- Quality degradation detection
- Automated rollback and retraining triggers
"""

import time
import json
from typing import Dict, List, Any, Annotated, Optional
from zenml import step
from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def deploy_best_prompt() -> Annotated[Dict[str, Any], ArtifactConfig(name="production_deployment_config")]:
    """
    Deploy the best-performing prompt to production environment.
    
    This demonstrates ZenML's enterprise deployment capabilities:
    - Automated selection of best-performing prompts
    - Zero-downtime deployment
    - Configuration management
    - Version control and rollback preparation
    """
    
    logger.info("🚀 Starting production deployment process")
    
    # Get the best-performing prompt from previous evaluations
    client = Client()
    
    # In a real implementation, this would query the model registry
    # for the highest-scoring prompt artifact
    try:
        # Mock deployment configuration
        deployment_config = {
            "deployment_id": f"prompt-deploy-{int(time.time())}",
            "environment": "production",
            "prompt_artifact_id": "best_prompt_v2_3",
            "model_config": {
                "model": "gpt-4",
                "temperature": 0.3,
                "max_tokens": 500,
                "timeout": 30
            },
            "deployment_strategy": "blue_green",
            "monitoring_config": {
                "quality_threshold": 8.0,
                "response_time_threshold": 3.0,
                "cost_threshold": 0.05,
                "monitoring_interval": 300  # 5 minutes
            },
            "rollback_config": {
                "automatic_rollback": True,
                "rollback_threshold": 7.5,
                "previous_version": "prompt_v2_2"
            },
            "traffic_routing": {
                "canary_percentage": 10,
                "full_deployment_after": 3600,  # 1 hour
                "gradual_rollout": True
            },
            "alerting": {
                "slack_webhook": "https://hooks.slack.com/services/...",
                "email_recipients": ["ml-team@company.com"],
                "alert_on": ["quality_degradation", "high_latency", "cost_spike"]
            }
        }
        
        # Simulate deployment process
        deployment_steps = [
            "Validating prompt artifact",
            "Preparing deployment environment",
            "Running pre-deployment tests",
            "Deploying to canary environment",
            "Running smoke tests",
            "Configuring monitoring",
            "Setting up alerting",
            "Enabling traffic routing"
        ]
        
        for step_name in deployment_steps:
            logger.info(f"  ✓ {step_name}")
            time.sleep(0.1)  # Simulate deployment time
        
        deployment_status = {
            "status": "deployed",
            "deployment_time": time.time(),
            "health_check": "passing",
            "traffic_percentage": deployment_config["traffic_routing"]["canary_percentage"],
            "monitoring_active": True
        }
        
        deployment_config.update(deployment_status)
        
        logger.info("✅ Production deployment completed successfully")
        logger.info(f"🎯 Deployed prompt: {deployment_config['prompt_artifact_id']}")
        logger.info(f"📊 Initial traffic: {deployment_config['traffic_percentage']}%")
        logger.info(f"⚡ Monitoring active with {deployment_config['monitoring_config']['monitoring_interval']}s intervals")
        
        return deployment_config
        
    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        
        # Return error configuration for demonstration
        return {
            "status": "failed",
            "error": str(e),
            "deployment_time": time.time(),
            "rollback_initiated": True
        }


@step
def monitor_production_performance(
    deployment_config: Dict[str, Any]
) -> Annotated[Dict[str, Any], ArtifactConfig(name="production_monitoring_data")]:
    """
    Monitor production performance and collect real-time metrics.
    
    Demonstrates ZenML's production monitoring capabilities:
    - Real-time quality monitoring
    - Performance metrics collection
    - Anomaly detection
    - Alert generation
    """
    
    logger.info("📊 Starting production performance monitoring")
    
    if deployment_config.get("status") != "deployed":
        logger.warning("⚠️ Deployment not active, skipping monitoring")
        return {"status": "skipped", "reason": "deployment_not_active"}
    
    # Simulate production monitoring data collection
    monitoring_data = {
        "deployment_id": deployment_config["deployment_id"],
        "monitoring_start_time": time.time(),
        "monitoring_interval": deployment_config["monitoring_config"]["monitoring_interval"],
        "metrics_collected": [],
        "alerts_generated": [],
        "health_status": "healthy"
    }
    
    # Simulate multiple monitoring cycles
    monitoring_cycles = 5
    
    for cycle in range(monitoring_cycles):
        logger.info(f"  📈 Monitoring cycle {cycle + 1}/{monitoring_cycles}")
        
        # Simulate metric collection
        cycle_metrics = _collect_production_metrics(deployment_config, cycle)
        monitoring_data["metrics_collected"].append(cycle_metrics)
        
        # Check for alerts
        alerts = _check_for_alerts(cycle_metrics, deployment_config["monitoring_config"])
        if alerts:
            monitoring_data["alerts_generated"].extend(alerts)
            logger.warning(f"  ⚠️ Generated {len(alerts)} alerts in cycle {cycle + 1}")
        
        # Update health status
        if any(alert["severity"] == "critical" for alert in alerts):
            monitoring_data["health_status"] = "critical"
        elif any(alert["severity"] == "warning" for alert in alerts):
            monitoring_data["health_status"] = "warning"
        
        time.sleep(0.2)  # Simulate monitoring interval
    
    # Generate monitoring summary
    monitoring_summary = _generate_monitoring_summary(monitoring_data)
    monitoring_data["summary"] = monitoring_summary
    
    logger.info("✅ Production monitoring completed")
    logger.info(f"📊 Collected {len(monitoring_data['metrics_collected'])} metric cycles")
    logger.info(f"🚨 Generated {len(monitoring_data['alerts_generated'])} alerts")
    logger.info(f"💚 Final health status: {monitoring_data['health_status']}")
    
    return monitoring_data


def _collect_production_metrics(deployment_config: Dict[str, Any], cycle: int) -> Dict[str, Any]:
    """Simulate production metrics collection."""
    
    import random
    
    # Simulate realistic metrics with some variation
    base_quality = 8.5
    base_response_time = 1.5
    base_cost = 0.025
    
    # Add some realistic variation and potential degradation over time
    quality_variation = random.uniform(-0.5, 0.3)
    time_variation = random.uniform(-0.2, 0.5)
    cost_variation = random.uniform(-0.005, 0.01)
    
    # Simulate potential issues in later cycles
    if cycle >= 3:
        quality_variation -= 0.2  # Slight quality degradation
        time_variation += 0.3     # Increased response time
    
    metrics = {
        "cycle": cycle + 1,
        "timestamp": time.time(),
        "quality_score": max(1.0, min(10.0, base_quality + quality_variation)),
        "response_time": max(0.1, base_response_time + time_variation),
        "cost_per_request": max(0.001, base_cost + cost_variation),
        "request_count": random.randint(450, 550),
        "success_rate": random.uniform(0.95, 1.0),
        "user_satisfaction": random.uniform(4.0, 5.0),
        "traffic_percentage": deployment_config["traffic_routing"]["canary_percentage"]
    }
    
    return metrics


def _check_for_alerts(metrics: Dict[str, Any], monitoring_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check metrics against thresholds and generate alerts."""
    
    alerts = []
    
    # Quality threshold check
    if metrics["quality_score"] < monitoring_config["quality_threshold"]:
        alerts.append({
            "type": "quality_degradation",
            "severity": "critical" if metrics["quality_score"] < 7.0 else "warning",
            "message": f"Quality score dropped to {metrics['quality_score']:.1f} (threshold: {monitoring_config['quality_threshold']})",
            "timestamp": time.time(),
            "metric_value": metrics["quality_score"],
            "threshold": monitoring_config["quality_threshold"]
        })
    
    # Response time check
    if metrics["response_time"] > monitoring_config["response_time_threshold"]:
        alerts.append({
            "type": "high_latency", 
            "severity": "critical" if metrics["response_time"] > 5.0 else "warning",
            "message": f"Response time increased to {metrics['response_time']:.1f}s (threshold: {monitoring_config['response_time_threshold']}s)",
            "timestamp": time.time(),
            "metric_value": metrics["response_time"],
            "threshold": monitoring_config["response_time_threshold"]
        })
    
    # Cost check
    if metrics["cost_per_request"] > monitoring_config["cost_threshold"]:
        alerts.append({
            "type": "cost_spike",
            "severity": "warning",
            "message": f"Cost per request increased to ${metrics['cost_per_request']:.3f} (threshold: ${monitoring_config['cost_threshold']:.3f})",
            "timestamp": time.time(),
            "metric_value": metrics["cost_per_request"],
            "threshold": monitoring_config["cost_threshold"]
        })
    
    # Success rate check
    if metrics["success_rate"] < 0.95:
        alerts.append({
            "type": "low_success_rate",
            "severity": "critical",
            "message": f"Success rate dropped to {metrics['success_rate']:.1%} (threshold: 95%)",
            "timestamp": time.time(),
            "metric_value": metrics["success_rate"],
            "threshold": 0.95
        })
    
    return alerts


def _generate_monitoring_summary(monitoring_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate monitoring summary with insights."""
    
    metrics = monitoring_data["metrics_collected"]
    alerts = monitoring_data["alerts_generated"]
    
    if not metrics:
        return {"status": "no_data"}
    
    # Calculate averages and trends
    avg_quality = sum(m["quality_score"] for m in metrics) / len(metrics)
    avg_response_time = sum(m["response_time"] for m in metrics) / len(metrics)
    avg_cost = sum(m["cost_per_request"] for m in metrics) / len(metrics)
    total_requests = sum(m["request_count"] for m in metrics)
    
    # Trend analysis (simple)
    quality_trend = "stable"
    if len(metrics) >= 3:
        recent_quality = sum(m["quality_score"] for m in metrics[-2:]) / 2
        early_quality = sum(m["quality_score"] for m in metrics[:2]) / 2
        if recent_quality < early_quality - 0.5:
            quality_trend = "declining"
        elif recent_quality > early_quality + 0.5:
            quality_trend = "improving"
    
    summary = {
        "monitoring_duration": time.time() - monitoring_data["monitoring_start_time"],
        "total_cycles": len(metrics),
        "total_requests_processed": total_requests,
        "average_metrics": {
            "quality_score": avg_quality,
            "response_time": avg_response_time,
            "cost_per_request": avg_cost
        },
        "trends": {
            "quality": quality_trend,
            "performance": "stable",  # Could be calculated similarly
            "cost": "stable"
        },
        "alert_summary": {
            "total_alerts": len(alerts),
            "critical_alerts": len([a for a in alerts if a["severity"] == "critical"]),
            "warning_alerts": len([a for a in alerts if a["severity"] == "warning"]),
            "most_common_alert": _get_most_common_alert_type(alerts)
        },
        "recommendations": _generate_recommendations(monitoring_data)
    }
    
    return summary


def _get_most_common_alert_type(alerts: List[Dict[str, Any]]) -> Optional[str]:
    """Get the most common alert type."""
    if not alerts:
        return None
    
    alert_counts = {}
    for alert in alerts:
        alert_type = alert["type"]
        alert_counts[alert_type] = alert_counts.get(alert_type, 0) + 1
    
    return max(alert_counts.items(), key=lambda x: x[1])[0] if alert_counts else None


def _generate_recommendations(monitoring_data: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on monitoring data."""
    
    recommendations = []
    alerts = monitoring_data["alerts_generated"]
    metrics = monitoring_data["metrics_collected"]
    
    # Quality-based recommendations
    quality_alerts = [a for a in alerts if a["type"] == "quality_degradation"]
    if quality_alerts:
        recommendations.append("Consider rolling back to previous prompt version due to quality degradation")
        recommendations.append("Investigate prompt quality issues and retrain if necessary")
    
    # Performance-based recommendations
    latency_alerts = [a for a in alerts if a["type"] == "high_latency"]
    if latency_alerts:
        recommendations.append("Optimize prompt length or switch to faster model")
        recommendations.append("Scale up infrastructure to handle load")
    
    # Cost-based recommendations
    cost_alerts = [a for a in alerts if a["type"] == "cost_spike"]
    if cost_alerts:
        recommendations.append("Review prompt complexity and optimize for cost")
        recommendations.append("Consider using smaller model for less critical requests")
    
    # General recommendations
    if len(alerts) == 0:
        recommendations.append("Performance is stable - consider gradual traffic increase")
        recommendations.append("Monitor for longer period before full deployment")
    
    return recommendations


@step
def trigger_retraining_if_needed(
    monitoring_data: Dict[str, Any]
) -> Annotated[Dict[str, Any], ArtifactConfig(name="retraining_decision")]:
    """
    Analyze monitoring data and trigger retraining if necessary.
    
    Demonstrates ZenML's automated ML lifecycle management:
    - Intelligent retraining decisions
    - Performance degradation detection
    - Automated pipeline triggering
    - Continuous improvement loops
    """
    
    logger.info("🔄 Analyzing retraining requirements")
    
    if monitoring_data.get("status") == "skipped":
        logger.info("⏭️ Skipping retraining analysis - no monitoring data")
        return {"status": "skipped", "reason": "no_monitoring_data"}
    
    # Analyze monitoring data for retraining triggers
    retraining_decision = _analyze_retraining_triggers(monitoring_data)
    
    if retraining_decision["should_retrain"]:
        logger.info("🚨 Retraining triggered!")
        
        # In a real implementation, this would trigger a new training pipeline
        retraining_config = _prepare_retraining_pipeline(monitoring_data, retraining_decision)
        
        logger.info(f"📋 Retraining strategy: {retraining_config['strategy']}")
        logger.info(f"🎯 Target improvements: {', '.join(retraining_config['target_improvements'])}")
        
        retraining_decision.update({
            "retraining_config": retraining_config,
            "pipeline_triggered": True,
            "estimated_completion": time.time() + 3600  # 1 hour estimate
        })
        
    else:
        logger.info("✅ No retraining required - performance within acceptable bounds")
        
        retraining_decision.update({
            "next_evaluation": time.time() + 86400,  # Check again in 24 hours
            "performance_status": "stable"
        })
    
    return retraining_decision


def _analyze_retraining_triggers(monitoring_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze monitoring data to determine if retraining is needed."""
    
    alerts = monitoring_data.get("alerts_generated", [])
    summary = monitoring_data.get("summary", {})
    
    triggers = []
    should_retrain = False
    
    # Quality degradation trigger
    critical_quality_alerts = [a for a in alerts if a["type"] == "quality_degradation" and a["severity"] == "critical"]
    if critical_quality_alerts:
        triggers.append({
            "type": "quality_degradation",
            "severity": "critical",
            "description": "Significant quality degradation detected",
            "evidence": f"{len(critical_quality_alerts)} critical quality alerts"
        })
        should_retrain = True
    
    # Performance degradation trigger
    if summary.get("trends", {}).get("quality") == "declining":
        triggers.append({
            "type": "performance_trend",
            "severity": "warning", 
            "description": "Declining performance trend detected",
            "evidence": "Quality scores showing downward trend"
        })
        # Only trigger retraining if multiple indicators
        if len(triggers) > 0:
            should_retrain = True
    
    # Cost efficiency trigger
    avg_cost = summary.get("average_metrics", {}).get("cost_per_request", 0)
    if avg_cost > 0.04:  # High cost threshold
        triggers.append({
            "type": "cost_efficiency",
            "severity": "warning",
            "description": "High cost per request detected", 
            "evidence": f"Average cost: ${avg_cost:.3f}"
        })
    
    # Success rate trigger
    success_rate_alerts = [a for a in alerts if a["type"] == "low_success_rate"]
    if success_rate_alerts:
        triggers.append({
            "type": "reliability", 
            "severity": "critical",
            "description": "Low success rate detected",
            "evidence": f"{len(success_rate_alerts)} success rate alerts"
        })
        should_retrain = True
    
    return {
        "should_retrain": should_retrain,
        "triggers": triggers,
        "analysis_timestamp": time.time(),
        "confidence": 0.9 if should_retrain else 0.7
    }


def _prepare_retraining_pipeline(
    monitoring_data: Dict[str, Any], 
    retraining_decision: Dict[str, Any]
) -> Dict[str, Any]:
    """Prepare retraining pipeline configuration."""
    
    triggers = retraining_decision["triggers"]
    
    # Determine retraining strategy based on triggers
    strategy = "incremental"
    target_improvements = []
    
    for trigger in triggers:
        if trigger["type"] == "quality_degradation":
            strategy = "full_retrain"
            target_improvements.append("quality_improvement")
        elif trigger["type"] == "cost_efficiency":
            target_improvements.append("cost_optimization")
        elif trigger["type"] == "reliability":
            strategy = "full_retrain"
            target_improvements.append("reliability_improvement")
    
    # Pipeline configuration
    retraining_config = {
        "strategy": strategy,
        "target_improvements": target_improvements,
        "training_data_sources": [
            "production_logs",
            "user_feedback", 
            "evaluation_results"
        ],
        "evaluation_criteria": [
            "quality_score",
            "response_time",
            "cost_efficiency",
            "user_satisfaction"
        ],
        "success_metrics": {
            "minimum_quality_improvement": 0.5,
            "maximum_cost_increase": 0.01,
            "minimum_success_rate": 0.97
        },
        "pipeline_steps": [
            "collect_training_data",
            "preprocess_feedback",
            "generate_improved_prompts",
            "evaluate_candidates", 
            "select_best_performer",
            "deploy_to_staging",
            "run_integration_tests",
            "deploy_to_production"
        ],
        "estimated_duration": "1-2 hours",
        "resource_requirements": {
            "cpu": "4 cores",
            "memory": "16GB",
            "gpu": "optional"
        }
    }
    
    return retraining_config