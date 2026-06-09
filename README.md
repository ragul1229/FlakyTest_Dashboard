# Flaky Test Detector & Explainer

Flaky Test Detector & Explainer is an AI-powered software testing assistant designed to identify and analyze unreliable test cases that produce inconsistent results across multiple executions. In modern software development, flaky tests can pass in one run and fail in another without any changes to the underlying code, making debugging difficult and reducing developer productivity.

The system executes test cases repeatedly, collects execution results, and detects tests exhibiting unstable behavior. Once a flaky test is identified, the application analyzes the test results and presents a detailed explanation of the possible root causes, such as timing issues, network latency, race conditions, environmental dependencies, or improper test design.

The solution provides an interactive Streamlit dashboard where users can upload test result files, view flaky test statistics, analyze individual test cases, access AI-generated explanations, and download comprehensive reports. By automating flaky test detection and root-cause analysis, the project helps development teams improve test reliability, reduce debugging effort, and enhance software quality.

### Key Features

* Automated flaky test identification
* Test stability scoring and analysis
* AI-generated root cause explanations
* Interactive dashboard for visualization
* Report generation and download
* User-friendly interface for test monitoring

### Technologies Used

* Python
* Streamlit
* Pandas
* JSON/CSV Processing
* AI-Based Explanation Engine

### Business Impact

The project reduces the time spent investigating unreliable tests, improves confidence in automated testing pipelines, and enables faster software delivery by helping teams quickly identify and resolve test instability issues.
