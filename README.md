# Hack the Future 2026 - some supply chain agent something (name coming soon!)

helloww!

## Overview

- **Agent:** `time_agent` — tells the current time in a specified city.
- **Model:** Gemini 2.5 Flash.
- **Tool:** `get_current_time(city)` — returns the current time (sample, more coming soon!)

The agent lives in `my_agent/agent.py` and can be run or integrated via the ADK CLI or your own entrypoint.

## Requirements

- **Python 3.11+**
- A [Google Cloud](https://cloud.google.com) project with Vertex AI / Gemini API enabled (for ADK/Gemini)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/clairelapatrada/htf26.git
cd htf26
```

### 2. Create a virtual environment (recommended)

Using Python 3.11:

```bash
python3.11 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

If `python3.11` isn’t in your PATH, use the full path (e.g. `/opt/homebrew/bin/python3.11` on macOS with Homebrew).

### 3. Install dependencies

Install the Agent Development Kit and its dependencies:

```bash
pip install --upgrade pip
pip install "google-adk>=1.18"
```

Optional: to install from the pinned list (may need version tweaks for your Python):

```bash
pip install -r requirements.txt
```

### 4. Configure Google Cloud authentication

Set up Application Default Credentials so the agent can call Gemini:

```bash
gcloud auth application-default login
```

Or set `GOOGLE_CLOUD_PROJECT` and use a service account key as needed for your environment.

## Running the agent

With the virtual environment activated:

```bash
adk run my_agent
```

```bash
python -c "from my_agent.agent import root_agent; print(root_agent.name)"
```

## Project structure

```
htf26/
├── README.md           # This file
├── requirements.txt    # Pinned dependencies (optional)
├── data.csv            # Data file (if used by your flows)
├── my_agent/
│   └── agent.py        # time_agent definition and get_current_time tool
└── venv/               # Virtual environment (create locally)
```

## Our team

- **1** — role
- **2** — role
- **3** — role
- **4** — role
- **5** — role
- **6** — role