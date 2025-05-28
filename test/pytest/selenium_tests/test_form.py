import os
import pytest
import tempfile
import subprocess
import time
import signal
from git import Repo
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import geckodriver_autoinstaller

@pytest.fixture(params=[
    {'name': 'default', 'data_channel': True, 'twcc': True, 'codec': 'H264', 'storage': False},
    {'name': 'no_data_channel', 'data_channel': False, 'twcc': True, 'codec': 'H264', 'storage': False},
    {'name': 'h265', 'data_channel': True, 'twcc': True, 'codec': 'H265', 'storage': False},
    {'name': 'storage', 'data_channel': True, 'twcc': True, 'codec': 'H264', 'storage': True}
])
def demo_config(request, tmp_path_factory):
    """Create demo_config.h with different options"""
    config_dir = tmp_path_factory.mktemp('config')
    config_path = config_dir / 'demo_config.h'
    
    config_content = f"""
#ifndef DEMO_CONFIG_H
#define DEMO_CONFIG_H

#define AWS_REGION "{os.environ.get('AWS_DEFAULT_REGION', 'us-west-2')}"
#define AWS_KVS_CHANNEL_NAME "KVSWebRTCChannel_1743093127"
#define AWS_KVS_AGENT_NAME "AWS-SDK-KVS"
#define AWS_CA_CERT_PATH "cert/cert.pem"

#define ENABLE_SCTP_DATA_CHANNEL {1 if request.param['data_channel'] else 0}U
#define ENABLE_TWCC_SUPPORT {1 if request.param['twcc'] else 0}U
#define JOIN_STORAGE_SESSION {1 if request.param['storage'] else 0}

#define USE_VIDEO_CODEC_H264 {1 if request.param['codec'] == 'H264' else 0}
#define USE_VIDEO_CODEC_H265 {1 if request.param['codec'] == 'H265' else 0}

#define AWS_ACCESS_KEY_ID "{os.environ['AWS_ACCESS_KEY_ID']}"
#define AWS_SECRET_ACCESS_KEY "{os.environ['AWS_SECRET_ACCESS_KEY']}"

#define AWS_MAX_VIEWER_NUM ( 2 )
#define AUDIO_OPUS 1

#endif /* DEMO_CONFIG_H */
"""
    config_path.write_text(config_content)
    return {'path': str(config_path), **request.param}

@pytest.fixture(scope="session", autouse=True)
def webrtc_setup(demo_config):
    """Set up WebRTC environment and start the master application"""
    # Get the absolute path to the master application
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    master_binary = os.path.join(project_root, 'build', 'WebRTCLinuxApplicationMaster')
    
    if not os.path.exists(master_binary):
        raise FileNotFoundError(f"WebRTCLinuxApplicationMaster binary not found at {master_binary}. Please ensure it is built.")
    
    # Build with custom config
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    build_dir = os.path.join(project_root, f'build_{demo_config["name"]}')
    os.makedirs(build_dir, exist_ok=True)
    
    # Copy config file to build directory
    subprocess.run(['cp', demo_config['path'], os.path.join(project_root, 'examples/demo_config/demo_config.h')], check=True)
    
    # Build the project
    subprocess.run(['cmake', '..'], cwd=build_dir, check=True)
    subprocess.run(['make'], cwd=build_dir, check=True)
    
    master_binary = os.path.join(build_dir, 'WebRTCLinuxApplicationMaster')
    
    # Start WebRTCLinuxApplicationMaster
    master_process = subprocess.Popen(
        [master_binary, '--config', demo_config['path']],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root
    )
    
    # Give the master application time to start and verify it's running
    time.sleep(2)
    
    # Check if the master process is still running
    if master_process.poll() is not None:
        stdout, stderr = master_process.communicate()
        raise RuntimeError(f"Master application failed to start. stdout: {stdout}, stderr: {stderr}")
    
    # Clone and set up the JS SDK
    with tempfile.TemporaryDirectory() as temp_dir:
        # Clone the repository
        repo_url = "https://github.com/awslabs/amazon-kinesis-video-streams-webrtc-sdk-js.git"
        repo = Repo.clone_from(repo_url, temp_dir)
        
        try:
            # Run npm install and build in root directory
            print("Installing dependencies in root directory...")
            result = subprocess.run(['npm', 'install'], cwd=temp_dir, check=True, capture_output=True, text=True)
            print(f"Root npm install output:\n{result.stdout}\n{result.stderr}")
            
            print("Building the project...")
            result = subprocess.run(['npm', 'run', 'build'], cwd=temp_dir, check=True, capture_output=True, text=True)
            print(f"Build output:\n{result.stdout}\n{result.stderr}")
            
            # Create web directory
            web_dir = os.path.join(temp_dir, 'examples', 'web')
            os.makedirs(web_dir, exist_ok=True)
            
            # List all files in examples directory
            examples_dir = os.path.join(temp_dir, 'examples')
            print(f"Files in examples directory: {os.listdir(examples_dir)}")
            
            # Find master example file
            master_files = [f for f in os.listdir(examples_dir) if 'master' in f.lower()]
            if not master_files:
                raise FileNotFoundError("No master example file found in examples directory")
            
            master_file = os.path.join(examples_dir, master_files[0])
            print(f"Found master file: {master_file}")
            
            # Copy files to web directory
            print("Setting up web directory...")
            subprocess.run(['cp', master_file, os.path.join(web_dir, 'index.html')], check=True)
            
            # Copy dist directory if it exists, otherwise look for bundle
            dist_dir = os.path.join(temp_dir, 'dist')
            bundle_dir = os.path.join(temp_dir, 'examples', 'bundle')
            
            if os.path.exists(dist_dir):
                subprocess.run(['cp', '-r', dist_dir, web_dir], check=True)
            elif os.path.exists(bundle_dir):
                subprocess.run(['cp', '-r', bundle_dir, web_dir], check=True)
            else:
                raise FileNotFoundError("Neither dist nor bundle directory found")
            
            print(f"Web directory contents: {os.listdir(web_dir)}")
            
            # Start the example server
            print("Starting web server...")
            server_process = subprocess.Popen(
                ['python3', '-m', 'http.server', '8443'],
                cwd=web_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Give the server time to start and verify it's running
            time.sleep(5)
            
            # Check if the server process is still running
            if server_process.poll() is not None:
                stdout, stderr = server_process.communicate()
                raise RuntimeError(f"Server failed to start. stdout: {stdout}, stderr: {stderr}")
            
            yield {
                'repo_url': repo_url,
                'master_process': master_process,
                'server_process': server_process,
                'example_url': 'http://localhost:8443/index.html'
            }
        finally:
            # Cleanup
            if 'server_process' in locals():
                server_process.send_signal(signal.SIGTERM)
                server_process.wait()
            master_process.send_signal(signal.SIGTERM)
            master_process.wait()

@pytest.fixture
def driver():
    # Setup Firefox driver
    geckodriver_autoinstaller.install()
    driver = webdriver.Firefox()
    driver.implicitly_wait(10)
    yield driver
    # Teardown
    driver.quit()

@pytest.fixture
def aws_credentials():
    """Provide AWS credentials from environment variables"""
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return {
        'access_key': os.environ['AWS_ACCESS_KEY_ID'],
        'secret_key': os.environ['AWS_SECRET_ACCESS_KEY'],
        'region': os.environ['AWS_DEFAULT_REGION']
    }

def test_webrtc_connection(driver, webrtc_setup, aws_credentials):
    """Test WebRTC connection between master application and JS SDK"""
    # Load the example page
    driver.get(webrtc_setup['example_url'])
    
    # Wait for and fill in AWS credentials
    access_key = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "accessKeyId"))
    )
    secret_key = driver.find_element(By.ID, "secretAccessKey")
    
    access_key.clear()
    access_key.send_keys(aws_credentials['access_key'])
    secret_key.clear()
    secret_key.send_keys(aws_credentials['secret_key'])
    
    # Set region
    region_select = driver.find_element(By.ID, "region")
    region_select.send_keys(aws_credentials['region'])
    
    # Set channel name
    channel_input = driver.find_element(By.ID, "channelName")
    channel_input.clear()
    channel_input.send_keys("KVSWebRTCChannel_1743093127")
    
    # Configure video settings
    video_checkbox = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox'][name='sendVideo']")
    if not video_checkbox.is_selected():
        video_checkbox.click()
    
    # Select resolution
    resolution_select = driver.find_element(By.CSS_SELECTOR, "select[name='resolution']")
    resolution_select.send_keys("1280x720")
    
    # Enable trickle ICE
    trickle_ice = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox'][name='useTrickleICE']")
    if not trickle_ice.is_selected():
        trickle_ice.click()
    
    # Start master
    start_button = driver.find_element(By.ID, "start-master")
    start_button.click()
    
    # Wait for connection in logs
    log_element = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".logs"))
    )
    
    # Verify connection in logs
    assert "Successfully established connection" in log_element.text

def test_data_channel(driver, webrtc_setup, demo_config):
    """Test WebRTC data channel functionality"""
    if not demo_config['data_channel']:
        pytest.skip("Data channel is disabled in this configuration")
    """Test WebRTC data channel functionality"""
    # Enable data channel if not already enabled
    data_channel_checkbox = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox'][name='openDataChannel']")
    if not data_channel_checkbox.is_selected():
        data_channel_checkbox.click()
    
    # Wait for data channel to be established
    log_element = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".logs"))
    )
    
    # Verify data channel in logs
    assert "Data channel opened" in log_element.text
    
    # Check master application logs
    master_output = webrtc_setup['master_process'].stdout.readline().decode()
    assert "Data channel established" in master_output
