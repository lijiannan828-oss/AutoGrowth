"""探索 Google Cloud Run v2 API 的实际结构

使用方法:
    python -m backend.scripts.explore_run_v2_api
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from google.cloud import run_v2
from app.core.config import settings
import os


def explore_executions_api():
    """探索 Executions API 的实际结构"""
    print("=" * 60)
    print("Google Cloud Run v2 API 结构探索")
    print("=" * 60)
    
    # 1. 检查客户端类
    print("\n1. 检查客户端类:")
    print(f"  JobsClient 方法:")
    jobs_methods = [m for m in dir(run_v2.JobsClient) if not m.startswith('_') and callable(getattr(run_v2.JobsClient, m))]
    print(f"    {jobs_methods[:10]}...")
    print(f"    有 list_executions? {hasattr(run_v2.JobsClient(), 'list_executions')}")
    
    print(f"\n  ExecutionsClient 方法:")
    exec_methods = [m for m in dir(run_v2.ExecutionsClient) if not m.startswith('_') and callable(getattr(run_v2.ExecutionsClient, m))]
    print(f"    {exec_methods[:10]}...")
    print(f"    有 list_executions? {hasattr(run_v2.ExecutionsClient(), 'list_executions')}")
    
    # 2. 列出执行
    print("\n2. 列出执行:")
    try:
        client = run_v2.ExecutionsClient()
        
        # Get job name
        job_name = settings.process_job_name.strip()
        if "/jobs/" in job_name:
            job_name = job_name.split("/jobs/")[-1]
        if not job_name:
            job_name = "drama-processor-job"
        
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or "fleet-blend-469520-n7"
        region = os.environ.get("GCP_REGION") or "us-central1"
        parent = f"projects/{project_id}/locations/{region}/jobs/{job_name}"
        
        print(f"  Parent: {parent}")
        
        request = run_v2.ListExecutionsRequest(parent=parent, page_size=5)
        response = client.list_executions(request=request)
        
        print(f"  找到 {len(response.executions)} 个执行")
        
        if response.executions:
            exec = response.executions[0]
            
            # 3. 检查 Execution 对象结构
            print("\n3. Execution 对象结构 (from list_executions):")
            attrs = [a for a in dir(exec) if not a.startswith('_')]
            print(f"  属性数量: {len(attrs)}")
            print(f"  关键属性: {[a for a in attrs if a in ['name', 'conditions', 'succeeded_count', 'failed_count', 'running_count', 'spec', 'template']]}")
            print(f"    有 spec? {hasattr(exec, 'spec')}")
            print(f"    有 template? {hasattr(exec, 'template')}")
            print(f"    有 conditions? {hasattr(exec, 'conditions')}")
            
            # 4. 检查条件对象
            if hasattr(exec, 'conditions'):
                conditions = exec.conditions
                print(f"\n4. Condition 对象结构:")
                if conditions:
                    cond = conditions[0]
                    cond_attrs = [a for a in dir(cond) if not a.startswith('_')]
                    print(f"  属性: {cond_attrs}")
                    print(f"    type_: {getattr(cond, 'type_', None)}")
                    print(f"    type: {getattr(cond, 'type', None)}")
                    print(f"    message: {getattr(cond, 'message', None)}")
                    print(f"    reason: {getattr(cond, 'reason', None)}")
                    print(f"    state: {getattr(cond, 'state', None)}")
            
            # 5. 获取完整详情
            print(f"\n5. Execution Details 对象结构 (from get_execution):")
            exec_details = client.get_execution(name=exec.name)
            detail_attrs = [a for a in dir(exec_details) if not a.startswith('_')]
            print(f"  属性数量: {len(detail_attrs)}")
            print(f"  关键属性: {[a for a in detail_attrs if a in ['name', 'conditions', 'succeeded_count', 'failed_count', 'running_count', 'template']]}")
            print(f"    有 template? {hasattr(exec_details, 'template')}")
            
            if hasattr(exec_details, 'template'):
                template = exec_details.template
                print(f"\n6. Template 对象结构:")
                template_attrs = [a for a in dir(template) if not a.startswith('_')]
                print(f"  属性: {template_attrs}")
                print(f"    有 containers? {hasattr(template, 'containers')}")
                
                if hasattr(template, 'containers'):
                    containers = template.containers
                    print(f"  容器数量: {len(containers) if containers else 0}")
                    if containers:
                        container = containers[0]
                        print(f"    有 env? {hasattr(container, 'env')}")
                        if hasattr(container, 'env'):
                            env_vars = container.env
                            print(f"    环境变量数量: {len(env_vars) if env_vars else 0}")
                            if env_vars:
                                print(f"    前5个环境变量:")
                                for env_var in env_vars[:5]:
                                    print(f"      {env_var.name} = {env_var.value}")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    explore_executions_api()

