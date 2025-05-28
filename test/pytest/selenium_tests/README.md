# WebRTC Integration Tests

This directory contains automated browser tests using Pytest and Selenium WebDriver to test WebRTC functionality between the WebRTCLinuxApplicationMaster binary and the Amazon Kinesis Video Streams WebRTC SDK JS example.

For a detailed explanation of the testing approach, architecture, and implementation details, see [testing-approach.md](testing-approach.md).

The tests automatically:

1. Build and run the WebRTCLinuxApplicationMaster
2. Clone and set up the WebRTC SDK JS example
3. Serve the example page using a local web server
4. Test the WebRTC connection and data transmission

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have Firefox browser installed on your system.
3. Make sure you have git installed on your system.
4. Make sure you have Node.js and npm installed for running the JS SDK example.
5. Build the WebRTCLinuxApplicationMaster:
   ```bash
   # From the project root directory
   mkdir -p build
   cd build
   cmake ..
   make
   ```
   This will create the WebRTCLinuxApplicationMaster binary in the build directory.
6. Set up AWS credentials by setting the following environment variables:
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
   - AWS_DEFAULT_REGION

## Test Files

- `test_form.py`: Selenium tests that verify WebRTC connection and data transmission

## Running Tests

To run the tests, execute the following command from this directory:
```bash
pytest test_form.py -v
```

## Test Cases and Configurations

The test suite runs each test case with different WebRTC configurations:

### Build Configurations
1. Default Configuration:
   - Data channel enabled
   - TWCC support enabled
   - H264 video codec
   - Storage session disabled

2. No Data Channel:
   - Data channel disabled
   - TWCC support enabled
   - H264 video codec
   - Storage session disabled

3. H265 Codec:
   - Data channel enabled
   - TWCC support enabled
   - H265 video codec
   - Storage session disabled

4. Storage Session:
   - Data channel enabled
   - TWCC support enabled
   - H264 video codec
   - Storage session enabled

### Test Cases
1. `test_webrtc_connection`:
   - Starts the WebRTCLinuxApplicationMaster binary
   - Clones and sets up the WebRTC JS SDK example
   - Configures AWS credentials and WebRTC settings
   - Establishes and verifies WebRTC connection
   - Monitors connection status in browser logs

2. `test_data_channel`:
   - Skipped when data channel is disabled
   - Enables and tests the WebRTC data channel
   - Verifies data channel establishment in browser logs
   - Confirms data channel setup in master application logs

## Notes

- Uses Firefox WebDriver (geckodriver) with automatic installation
- Manages AWS credentials securely through environment variables
- Handles WebRTC SDK repository cloning and setup
- Automatically manages all processes and cleanup
- Includes proper wait conditions for WebRTC operations
- Shares WebRTC setup across tests for efficiency
- Provides detailed logging from both browser and master application

## Environment Variables

Required AWS credentials:
- `AWS_ACCESS_KEY_ID`: Your AWS access key ID
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key
- `AWS_DEFAULT_REGION`: Your AWS region (e.g., eu-central-1)

The test will validate that all required environment variables are set before running.

## Troubleshooting

1. If you see "WebRTCLinuxApplicationMaster binary not found":
   - Ensure you've built the project following the build instructions above
   - Verify the binary exists in the `build` directory
   - Check the binary permissions are correct

2. If npm commands fail:
   - Ensure Node.js and npm are installed
   - Try running `npm cache clean --force` before installation
   - Check the detailed error output in the test logs

3. If the web server fails to start:
   - Ensure port 8443 is available
   - Check if Python 3 is installed and accessible
   - Verify the example files were copied correctly

4. If WebRTC connection fails:
   - Verify your AWS credentials are correct
   - Check the browser logs for detailed error messages
   - Ensure the KVS channel name is valid and accessible
   - Verify the master application is running (check process output)

5. SDK structure issues:
   - The test looks for a master example file (e.g., master.html) in the examples directory
   - It will use either the dist/ or examples/bundle/ directory for SDK files
   - The test automatically creates a web directory and sets up the server

6. Common error messages:
   - "No master example file found": The SDK structure has changed, check examples directory
   - "Neither dist nor bundle directory found": Build process failed or structure changed
   - "Server failed to start": Port 8443 might be in use or you lack permissions
   - "Connection timeout": Network issues, AWS credentials, or firewall settings
   - "npm run build failed": Node.js version mismatch or missing dependencies

7. Build process:
   - The test will first try to build the SDK using npm
   - It will look for built files in both dist/ and bundle/ directories
   - All necessary files are copied to a temporary web directory
   - The web server serves files from this temporary directory

## GitHub Actions Integration

The tests are configured to run automatically in GitHub Actions:

1. Setup in your repository:
   - Go to Settings > Secrets and variables > Actions
   - Add the following secrets:
     * `AWS_ACCESS_KEY_ID`
     * `AWS_SECRET_ACCESS_KEY`

2. The workflow will:
   - Run on push to main and pull requests
   - Set up Python, Node.js, and Firefox
   - Build the WebRTCLinuxApplicationMaster
   - Run tests in headless mode
   - Upload test logs as artifacts

3. View test results:
   - Go to Actions tab in your repository
   - Select the latest workflow run
   - Check test output and downloaded artifacts
   - Logs are available even if tests fail

4. Workflow configuration:
   - Located in `.github/workflows/webrtc-tests.yml`
   - Uses Ubuntu latest runner
   - Runs Firefox in headless mode
   - Preserves logs for debugging
