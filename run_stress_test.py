import concurrent.futures
import subprocess
import time
import os
import shutil

QUERIES = [
    "Optimizing RAG systems with knowledge graphs",
    "Multi-agent orchestration patterns for software engineering",
    "Self-healing mechanisms in distributed systems"
]

def run_agent(query, idx):
    artifacts_dir = f"artifacts_test_{idx}"
    if os.path.exists(artifacts_dir):
        shutil.rmtree(artifacts_dir)
    os.makedirs(artifacts_dir)
    
    # 각 프로세스에 대해 별도의 환경 변수 설정
    env = os.environ.copy()
    env["ARTIFACTS_DIR"] = artifacts_dir
    env["PYTHONUNBUFFERED"] = "1"
    
    # OPENAI_API_KEY가 없다면 mock 모드로 실행
    args = ["python3", "main.py", "--auto", "--query", query]
    if not env.get("OPENAI_API_KEY"):
        args.append("--mock")
    
    print(f"[{idx}] Starting: {query}")
    start_time = time.time()
    
    stdout_content = ""
    stderr_content = ""
    return_code = -1
    success = False
    
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=600  # 10분 타임아웃
        )
        duration = time.time() - start_time
        stdout_content = result.stdout
        stderr_content = result.stderr
        return_code = result.returncode
        success = return_code == 0
        status = "SUCCESS" if success else "FAILED"
        print(f"[{idx}] {status} in {duration:.2f}s.")
        
    except subprocess.TimeoutExpired as e:
        duration = time.time() - start_time
        stdout_content = e.stdout if e.stdout else "(no stdout captured)"
        stderr_content = e.stderr if e.stderr else "(no stderr captured)"
        print(f"[{idx}] TIMEOUT after {duration:.2f}s")
        success = False
        
    except Exception as e:
        duration = time.time() - start_time
        stderr_content = f"Exception: {str(e)}"
        print(f"[{idx}] EXCEPTION: {e}")
        success = False

    log_file = f"test_log_{idx}.txt"
    with open(log_file, "w") as f:
        f.write(f"CMD: {' '.join(args)}\n")
        f.write(f"EXIT CODE: {return_code}\n")
        f.write("STDOUT:\n")
        f.write(stdout_content)
        f.write("\nSTDERR:\n")
        f.write(stderr_content)
        
    print(f"[{idx}] Log saved to {log_file}")
    
    # 간단한 결과 분석
    if "Quality gate PASSED" in stdout_content:
        print(f"[{idx}] Quality Gate: PASSED")
    elif "Quality gate FAILED" in stdout_content:
        print(f"[{idx}] Quality Gate: FAILED")
            
    return success

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(run_agent, q, i): i for i, q in enumerate(QUERIES)}
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"[{idx}] Exception: {e}")

if __name__ == "__main__":
    main()
