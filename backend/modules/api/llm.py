"""
LLM API endpoints.
Handles AI analysis and insights.
"""

import time
import logging
from datetime import datetime

from flask import request

from modules.decorators import generate_response
from modules.constants import SystemConstants


class LLMAPI:
    """
    LLM API endpoints.
    
    @param auth_manager: Authentication manager instance
    @param config_manager: Configuration manager instance
    @param cache_manager: Cache manager instance
    """
    
    def __init__(self, auth_manager, config_manager, cache_manager):
        self.auth_manager = auth_manager
        self.config_manager = config_manager
        self.cache_manager = cache_manager
    
    def analyze_tasks_llm_endpoint(self):
        """
        Endpoint for analyzing tasks via LLM.
        Requires can_use_llm permission.
        In demo mode returns sample data.
        
        Body: JSON with analysis parameters (LLMAnalysisRequest model)
        
        @return: JSON with analysis results
        """
        analysis_request = request.validated_data
        user_info = request.user_info
        
        logging.info(f"LLM analysis request from user: {user_info['telegram_username']}")
        logging.debug(f"Analysis parameters: {analysis_request.model_dump()}")
        
        # Check LLM request quota (always OK in demo mode)
        quota = self.auth_manager.get_user_llm_quota(user_info['telegram_username'])
        
        # Generate cache key
        cache_key = self.cache_manager.generate_key(
            'llm_analysis',
            time_period=analysis_request.time_period,
            metrics=','.join(sorted(analysis_request.metrics)),
            date=datetime.now().strftime('%Y-%m-%d')
        )
        
        # Check cache
        cached_result = self.cache_manager.get(cache_key)
        if cached_result:
            cached_result['meta']['cache_hit'] = True
            logging.debug(f"Using cached LLM analysis result")
            return generate_response(
                cached_result['data'], 
                meta=cached_result.get('meta', {}),
                config_manager=self.config_manager
            )
        
        # DEMO DATA (instead of real LLM analysis)
        # In a real system this would call OpenAI API
        demo_analysis_result = {
            'report_id': f"llm_rep_{int(time.time())}",
            'generated_at': datetime.now().isoformat(),
            'time_period': analysis_request.time_period,
            'analysis': {
                'summary': {
                    'total_tasks': 45,
                    'completed': 32,
                    'completion_rate': "71%",
                    'in_progress': 8,
                    'overdue': 5,
                    'avg_completion_time': "2.3 days"
                },
                'productivity_metrics': {
                    'top_performers': [
                        {"username": "@developer_alex", "tasks_completed": 12, "completion_rate": "92%"},
                        {"username": "@manager_anna", "tasks_completed": 10, "completion_rate": "100%"}
                    ],
                    'team_productivity_score': 7.8,
                    'daily_completion_trend': [5, 7, 6, 8, 4, 3, 5]
                },
                'bottlenecks': [
                    {
                        'area': 'code_review',
                        'impact': 'high',
                        'avg_delay': '1.5 days',
                        'affected_tasks': [101, 103, 107],
                        'recommendation': 'Implement automatic code checks'
                    }
                ],
                'team_performance': {
                    'workload_distribution': {
                        '@developer_alex': '35%',
                        '@manager_anna': '25%',
                        'others': '40%'
                    },
                    'collaboration_score': 6.2,
                    'suggested_adjustments': [
                        'Distribute workload more evenly',
                        'Assign mentor for new employees'
                    ]
                }
            },
            'recommendations': [
                'Implement automatic deadline reminders',
                'Set limit for concurrent tasks (max 5 per person)'
            ] if analysis_request.include_recommendations else [],
            'predictions': {
                'next_week_completion': '38-42 tasks',
                'potential_bottlenecks': ['testing', 'integration'],
                'suggested_actions': [
                    'Start working on high priority tasks early in the week',
                    'Schedule code reviews for Wednesday and Friday'
                ]
            }
        }
        
        # Form full response
        response_data = {
            'status': 'success',
            'data': demo_analysis_result,
            'meta': {
                'timestamp': datetime.now().isoformat(),
                'request_id': f"req_llm_{int(time.time())}",
                'tokens_used': 1450,
                'cache_hit': False,
                'llm_model': 'demo-mode',
                'note': 'This is demo data. In a real system this would call LLM API.',
                'quota_info': quota
            }
        }
        
        # Save to cache
        self.cache_manager.set(cache_key, response_data, ttl=3600)  # 1 hour
        
        logging.info(f"LLM analysis completed for user {user_info['telegram_username']} (demo mode)")
        return generate_response(
            demo_analysis_result, 
            meta=response_data['meta'],
            config_manager=self.config_manager
        )