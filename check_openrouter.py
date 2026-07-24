
import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM

print("🚀 Starting OpenRouter connection test (Perfected Disguise Strategy)...")
load_dotenv()

try:
    # 1. Grab your OpenRouter key and clean it
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip('"').strip("'").strip()
    
    if not openrouter_key:
        raise ValueError("❌ OPENROUTER_API_KEY is missing from .env!")

    print("✅ OpenRouter API key found.")

    # 2. "Disguise" it as standard OpenAI credentials for LiteLLM
    # This forces litellm to use its most reliable authentication pathway.
    os.environ["OPENAI_API_KEY"] = openrouter_key
    os.environ["OPENAI_API_BASE"] = "https://openrouter.ai/api/v1"
    print("✅ Disguised key and base URL as OpenAI environment variables.")

    # 3. Initialize CrewAI's LLM using the 'openai/' prefix
    # This tells LiteLLM to use the standard OpenAI client, which correctly
    # attaches the Authorization header to the custom base URL.
    llm = LLM(
        model="openai/mistralai/mistral-7b-instruct:free",
        extra_headers={
            "HTTP-Referer": "https://github.com/Omar-Eldaly/ai-video-generation-app",
            "X-Title": "Sprints AI Video Generation App",
        }
    )
    print("✅ CrewAI LLM client initialized with 'openai/' model prefix.")

    # Create a simple test agent
    test_agent = Agent(
        role="Test Agent",
        goal="Confirm LLM connection.",
        backstory="A test agent.",
        llm=llm,
        verbose=False
    )
    print("✅ Test agent created.")

    # Create a simple test task
    test_task = Task(
        description="Say 'Hello, World!'",
        expected_output="The string 'Hello, World!'",
        agent=test_agent
    )
    print("✅ Test task created.")

    # Create a crew and run the task
    test_crew = Crew(agents=[test_agent], tasks=[test_task])
    print("⏳ Sending a test prompt to OpenRouter via Crew...")
    
    result = test_crew.kickoff()

    if result:
        print(f"\n🎉 SUCCESS! OpenRouter Response:\n{result}")
    else:
        print("\n❌ FAILURE: The connection was successful, but the response was empty.")

except Exception as e:
    print(f"\n❌❌❌ TEST FAILED ❌❌❌")
    print(f"An error occurred: {e}")