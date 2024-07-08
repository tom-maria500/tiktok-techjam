# tiktok-techjam
# IntelliTok: Smart Sales Assistant for TikTok

IntelliTok is an advanced sales assistant application designed to streamline and enhance the sales process for TikTok's advertising team. It leverages AI and automation to improve productivity, client relationships, and data-driven decision-making.

## Features

- **Client Dashboard**: Centralized view of client information with dynamically generated to-do lists and sentiment analysis.
- **File Upload**: Easy document management with automatic information extraction.
- **Email Summaries**: Condenses lengthy email exchanges into actionable points.
- **AI Chat Assistant**: Provides insights and strategic advice for client interactions.
- **Smart Calendar**: Integrated scheduling with automatic meeting transcription and analysis.
- **Business Intelligence**: Comprehensive analytics on sales pipeline and performance metrics.
- **Profile Management**: Personalized user profiles with performance tracking.

##Live Demo
https://youtu.be/Y-3WkBcNKDw

## Installation

1. Clone the repository:
2. Install the required dependencies:
3. Set up environment variables:
- Create a `.env` file in the root directory
- Add the following variables:
  ```
  OPEN_API_KEY_CLIENT_DASHBOARD=your_openai_api_key
  ```
4. Set up Google OAuth:
- Place your `clientSecrets.json` file in the root directory
- Update the `REDIRECT_URI` in `login.py` if necessary
5. Set up Google Cloud Speech-to-Text:
- Place your `smart_chat_service_account.json` file in the root directory

## Usage

Run the Streamlit app:
## File Structure

- `login.py`: Handles user authentication and initial app setup
- `app.py`: Main application file with dashboard and navigation
- `clientDashboard.py`: Client-specific dashboard functionality
- `clientDashboardFunctions.py`: Helper functions for the client dashboard
- `gmail_utils.py`: Utilities for handling Gmail integration

## Dependencies

- Streamlit
- OpenAI
- Google Cloud Speech
- Plotly
- Pandas
- NumPy
- PyAudio

## Acknowledgments

- TikTok for the inspiration and opportunity to participate in TechJam 2024
- OpenAI for powering our AI features
- Google Cloud for Speech-to-Text capabilities
