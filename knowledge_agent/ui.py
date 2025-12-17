#!/usr/bin/env python3
"""
Web UI for Document Question Answering Agent

A Gradio-based interface for easier testing and interaction with the agent.
"""

import os
import sys
import asyncio
import json
import pandas as pd
from pathlib import Path
import gradio as gr
from agent import DocumentAgent

# Add parent directory to path to import config_loader
sys.path.insert(0, str(Path(__file__).parent.parent))
from config_loader import load_config

# Load environment variables (checks local and parent directories)
load_config()


class AgentUI:
    """Web UI wrapper for the Document Agent."""

    def __init__(self):
        """Initialize the UI and agent."""
        self.agent = None
        self.tools_loaded = False
        self.tool_calls = []
        self.setup_complete = False
        self.init_error = None
        self.current_images = []  # Track images used in current conversation

    def set_agent(self, agent):
        """Set the initialized agent."""
        self.agent = agent
        self.setup_complete = True
        self.tools_loaded = True

        # Set up tool call callback
        def tool_callback(name, args, result):
            self.tool_calls.append({
                'name': name,
                'args': str(args),
                'result': result
            })

            # Track images that were analyzed
            if name == "analyze_image":
                print(f"DEBUG: analyze_image called with args type: {type(args)}, value: {args}")

                # Parse args if it's a string
                if isinstance(args, str):
                    try:
                        import json
                        args = json.loads(args.replace("'", '"'))
                    except:
                        args = {}

                if isinstance(args, dict) and "image_path" in args:
                    image_path = args["image_path"]
                    print(f"DEBUG: Found image_path: {image_path}, exists: {os.path.exists(image_path)}")

                    if os.path.exists(image_path) and image_path not in [img["path"] for img in self.current_images]:
                        self.current_images.append({
                            "path": image_path,
                            "question": args.get("question", "No specific question")
                        })
                        print(f"DEBUG: Added image to gallery. Total images: {len(self.current_images)}")
                    elif image_path in [img["path"] for img in self.current_images]:
                        print(f"DEBUG: Image already in gallery")
                    else:
                        print(f"DEBUG: Image file does not exist at path: {image_path}")

        self.agent.tool_call_callback = tool_callback

    def get_status(self):
        """Get initialization status."""
        if self.init_error:
            return f"✗ Error initializing agent:\n\n{self.init_error}\n\nPlease check your .env configuration."

        if not self.setup_complete:
            return "⏳ Agent not initialized yet"

        status = "✓ Agent initialized successfully!\n\n"
        status += f"**Provider:** {self.agent.provider.upper()}\n"
        status += f"**Model:** {self.agent.model}\n"
        status += f"**Tools loaded:** {len(self.agent.tools)}\n\n"
        status += "**Available tools:**\n"
        for tool in self.agent.tools:
            status += f"  • {tool['name']} ({tool['server']})\n"

        return status

    def ask_question(self, question, history):
        """
        Process a question and return the response.

        Args:
            question: User's question
            history: Chat history (list of message dicts)

        Returns:
            Updated history and tool calls log
        """
        if not self.setup_complete:
            error_msg = "Agent not initialized. Please check the System Status panel."
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": error_msg})
            return history, self.format_tool_calls(), self.get_images_gallery()

        if not question or not question.strip():
            error_msg = "Please enter a question."
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": error_msg})
            return history, self.format_tool_calls(), self.get_images_gallery()

        # Clear previous tool calls and images for this question
        self.tool_calls = []
        self.current_images = []

        try:
            # Run async question in new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(self.agent.answer_question(question))
            finally:
                loop.close()

            # Add to history as message dicts
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": response})

        except Exception as e:
            import traceback
            error_msg = f"**Error:** {str(e)}\n\n```\n{traceback.format_exc()}\n```"
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": error_msg})

        return history, self.format_tool_calls(), self.get_images_gallery()

    def format_tool_calls(self):
        """Format tool calls for display."""
        if not self.tool_calls:
            return "No tool calls yet. Ask a question to see tool usage."

        formatted = "## Tool Calls\n\n"
        for i, call in enumerate(self.tool_calls, 1):
            formatted += f"### {i}. {call['name']}\n\n"
            formatted += f"**Arguments:**\n```json\n{call['args']}\n```\n\n"
            result_preview = call['result'][:300] + "..." if len(call['result']) > 300 else call['result']
            formatted += f"**Result:**\n```\n{result_preview}\n```\n\n"
            formatted += "---\n\n"

        # Add image tracking info
        if self.current_images:
            formatted += f"\n**Images tracked:** {len(self.current_images)}\n"
            for img in self.current_images:
                formatted += f"  • {img['path']}\n"

        return formatted

    def get_images_gallery(self):
        """Get list of image paths for gallery display."""
        if not self.current_images:
            print("DEBUG: No images to display")
            return []

        image_paths = [img["path"] for img in self.current_images]
        print(f"DEBUG: Returning {len(image_paths)} images for gallery: {image_paths}")
        return image_paths

    def get_config_info(self):
        """Get current configuration information."""
        config = "## Current Configuration\n\n"
        config += f"**AI Provider:** `{os.getenv('AI_PROVIDER', 'not set')}`\n\n"

        if os.getenv('AI_PROVIDER', 'anthropic') == 'anthropic':
            config += f"**Model:** `{os.getenv('ANTHROPIC_MODEL', 'default')}`\n"
            config += f"**API Key:** {'✓ Set' if os.getenv('ANTHROPIC_API_KEY') else '✗ Not set'}\n\n"
        else:
            config += f"**Model:** `{os.getenv('OPENAI_MODEL', 'default')}`\n"
            config += f"**API Key:** {'✓ Set' if os.getenv('OPENAI_API_KEY') else '✗ Not set'}\n\n"

        config += f"**Max Tokens:** `{os.getenv('MAX_TOKENS', '4096')}`\n"
        config += f"**Temperature:** `{os.getenv('TEMPERATURE', '0.7')}`\n\n"

        config += "### MCP Servers\n\n"
        config += f"**Elastic Search:**\n"
        config += f"  - Command: `{os.getenv('ELASTIC_SEARCH_MCP_COMMAND', 'not set')}`\n"
        elastic_args = os.getenv('ELASTIC_SEARCH_MCP_ARGS', 'not set')
        if len(elastic_args) > 60:
            elastic_args = elastic_args[:60] + "..."
        config += f"  - Args: `{elastic_args}`\n\n"

        config += f"**Image Analysis:**\n"
        config += f"  - Command: `{os.getenv('IMAGE_ANALYSIS_MCP_COMMAND', 'not set')}`\n"
        image_args = os.getenv('IMAGE_ANALYSIS_MCP_ARGS', 'not set')
        if len(image_args) > 60:
            image_args = image_args[:60] + "..."
        config += f"  - Args: `{image_args}`\n\n"

        config += "### System Prompt\n\n"
        prompt = os.getenv('SYSTEM_PROMPT', 'Using default prompt')
        config += f"```\n{prompt[:300]}{'...' if len(prompt) > 300 else ''}\n```\n"

        return config

    def run_evaluation(self, questions_file, tokens_per_minute=30000, delay_between_questions=10.0, enable_rate_limiting=True, eval_provider="openai", eval_model=None, progress=gr.Progress()):
        """
        Run evaluation on questions from a file.

        Args:
            questions_file: Path to JSON file with questions
            tokens_per_minute: Maximum tokens per minute for API calls
            delay_between_questions: Fixed delay in seconds between questions
            enable_rate_limiting: Whether to enable rate limiting
            progress: Gradio progress tracker

        Returns:
            Tuple of (results_df, summary_text, detailed_results)
        """
        if not self.setup_complete:
            error_msg = "❌ Agent not initialized. Please check the System Status panel."
            return None, error_msg, ""

        try:
            import time
            from deepeval.models.base_model import DeepEvalBaseLLM

            # Custom evaluation model
            class CustomEvaluationModel(DeepEvalBaseLLM):
                def __init__(self, provider, model):
                    self.provider = provider.lower()
                    self.api_key = os.getenv(f"{provider.upper()}_API_KEY")

                    if self.provider == "openai":
                        from openai import OpenAI
                        self.model_name = model or "gpt-4o-mini"
                        self.client = OpenAI(api_key=self.api_key)
                    elif self.provider == "anthropic":
                        from anthropic import Anthropic
                        self.model_name = model or "claude-3-5-haiku-20241022"
                        self.client = Anthropic(api_key=self.api_key)

                def load_model(self):
                    return self.client

                def generate(self, prompt):
                    if self.provider == "openai":
                        response = self.client.chat.completions.create(
                            model=self.model_name,
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.0,
                        )
                        return response.choices[0].message.content
                    elif self.provider == "anthropic":
                        response = self.client.messages.create(
                            model=self.model_name,
                            max_tokens=4096,
                            temperature=0.0,
                            messages=[{"role": "user", "content": prompt}],
                        )
                        return response.content[0].text

                async def a_generate(self, prompt):
                    return self.generate(prompt)

                def get_model_name(self):
                    return self.model_name

            # Create evaluation model
            evaluation_model = None
            if eval_provider and eval_model:
                evaluation_model = CustomEvaluationModel(eval_provider, eval_model)
                progress(0, desc=f"Using {eval_model} for evaluation...")

            # Token rate limiter setup
            class TokenRateLimiter:
                def __init__(self, tokens_per_minute, delay_between_questions):
                    self.tokens_per_minute = tokens_per_minute
                    self.delay_between_questions = delay_between_questions
                    self.tokens_used = 0
                    self.window_start = time.time()
                    self.last_request_time = 0
                    # DeepEval uses ~4 metric evaluations per question
                    self.estimated_tokens_per_eval = 11000

                def estimate_tokens(self, text):
                    return len(text) // 4

                def wait_if_needed(self, estimated_tokens=None):
                    if estimated_tokens is None:
                        estimated_tokens = self.estimated_tokens_per_eval

                    current_time = time.time()

                    # Enforce minimum delay between questions
                    if self.last_request_time > 0:
                        time_since_last = current_time - self.last_request_time
                        if time_since_last < self.delay_between_questions:
                            delay_needed = self.delay_between_questions - time_since_last
                            progress(0, desc=f"⏳ Delay between questions ({delay_needed:.1f}s)...")
                            time.sleep(delay_needed)
                            current_time = time.time()

                    # Token-based rate limiting
                    elapsed = current_time - self.window_start

                    if elapsed >= 60:
                        self.tokens_used = 0
                        self.window_start = current_time
                    else:
                        if self.tokens_used + estimated_tokens > self.tokens_per_minute:
                            wait_time = 60 - elapsed
                            if wait_time > 0:
                                progress(0, desc=f"⏳ Token limit - waiting {wait_time:.0f}s...")
                                time.sleep(wait_time)
                                self.tokens_used = 0
                                self.window_start = time.time()

                    self.tokens_used += estimated_tokens
                    self.last_request_time = time.time()

            rate_limiter = TokenRateLimiter(tokens_per_minute, delay_between_questions) if enable_rate_limiting else None
            # Import evaluation dependencies
            from deepeval import evaluate
            from deepeval.metrics import (
                AnswerRelevancyMetric,
                FaithfulnessMetric,
                ContextualPrecisionMetric,
                ContextualRecallMetric,
            )
            from deepeval.test_case import LLMTestCase

            # Read questions file
            if isinstance(questions_file, str):
                # File path provided
                with open(questions_file, 'r') as f:
                    questions = json.load(f)
            else:
                # File object from Gradio upload
                questions = json.load(questions_file)

            progress(0, desc="Starting evaluation...")

            # Prepare test cases
            test_cases = []
            questions_data = []

            # Process each question
            total = len(questions)
            for i, q in enumerate(questions):
                progress((i / total), desc=f"Processing question {i+1}/{total}...")

                # Apply rate limiting
                if rate_limiter:
                    estimated = rate_limiter.estimate_tokens(
                        q['question'] + q.get('ground_truth', '')
                    )
                    rate_limiter.wait_if_needed(estimated)

                # Clear tool calls for this question
                self.tool_calls = []
                captured_contexts = []

                # Set up context capture
                original_callback = self.agent.tool_call_callback

                def capture_context(name, args, result):
                    # Call original callback
                    if original_callback:
                        original_callback(name, args, result)
                    # Capture contexts
                    if name == "search_documents":
                        captured_contexts.append(result)

                self.agent.tool_call_callback = capture_context

                try:
                    # Run async question
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        answer = loop.run_until_complete(
                            self.agent.answer_question(q['question'])
                        )
                    finally:
                        loop.close()

                    # Use captured contexts or fallback to provided contexts
                    retrieval_context = captured_contexts if captured_contexts else q.get('contexts', [])

                    # Create DeepEval test case
                    test_case = LLMTestCase(
                        input=q['question'],
                        actual_output=answer,
                        expected_output=q['ground_truth'],
                        retrieval_context=retrieval_context
                    )

                    test_cases.append(test_case)
                    questions_data.append({
                        'question': q['question'],
                        'answer': answer,
                        'contexts': retrieval_context,
                        'ground_truth': q['ground_truth']
                    })

                except Exception as e:
                    # Add error entry
                    test_case = LLMTestCase(
                        input=q['question'],
                        actual_output=f"Error: {str(e)}",
                        expected_output=q['ground_truth'],
                        retrieval_context=q.get('contexts', [])
                    )
                    test_cases.append(test_case)
                    questions_data.append({
                        'question': q['question'],
                        'answer': f"Error: {str(e)}",
                        'contexts': q.get('contexts', []),
                        'ground_truth': q['ground_truth']
                    })

                # Restore original callback
                self.agent.tool_call_callback = original_callback

            progress(0.8, desc="Running DeepEval evaluation...")

            # Define metrics with custom model if specified
            metric_kwargs = {"threshold": 0.7}
            if evaluation_model:
                metric_kwargs["model"] = evaluation_model

            metrics = [
                AnswerRelevancyMetric(**metric_kwargs),
                FaithfulnessMetric(**metric_kwargs),
                ContextualPrecisionMetric(**metric_kwargs),
                ContextualRecallMetric(**metric_kwargs),
            ]

            # Evaluate with deepeval
            evaluate(test_cases=test_cases, metrics=metrics)

            progress(1.0, desc="Evaluation complete!")

            # Extract scores and create dataframe
            results_data = []
            metric_scores = {
                'answer_relevancy': [],
                'faithfulness': [],
                'contextual_precision': [],
                'contextual_recall': []
            }

            for i, test_case in enumerate(test_cases):
                row = {'question': questions_data[i]['question'][:50] + '...'}

                # Extract metric scores
                for metric in metrics:
                    metric_name = metric.__class__.__name__.replace('Metric', '').lower()
                    # Convert camelCase to snake_case
                    metric_name = ''.join(['_'+c.lower() if c.isupper() else c for c in metric_name]).lstrip('_')

                    # Try to get score from test case
                    score = getattr(test_case, f"{metric.__class__.__name__.replace('Metric', '').lower()}_score", None)
                    if score is not None:
                        row[metric_name] = score
                        if metric_name in metric_scores:
                            metric_scores[metric_name].append(score)
                    else:
                        row[metric_name] = 0.0

                results_data.append(row)

            results_df = pd.DataFrame(results_data)

            # Create summary
            summary = "## 📊 Evaluation Summary\n\n"
            summary += f"**Total Questions Evaluated:** {len(questions)}\n\n"
            summary += "### Average Scores\n\n"

            for metric_name, scores in metric_scores.items():
                if scores:
                    avg_score = sum(scores) / len(scores)
                    summary += f"- **{metric_name.replace('_', ' ').title()}:** {avg_score:.3f}\n"

            # Create detailed results
            detailed = "## 📝 Detailed Results\n\n"
            for i, data in enumerate(questions_data):
                detailed += f"### Question {i+1}\n"
                detailed += f"**Q:** {data['question'][:100]}...\n\n"
                for metric_name in metric_scores.keys():
                    if i < len(results_data) and metric_name in results_data[i]:
                        score = results_data[i][metric_name]
                        detailed += f"- {metric_name}: {score:.3f}\n"
                detailed += "\n---\n\n"

            return results_df, summary, detailed

        except Exception as e:
            import traceback
            error_msg = f"❌ **Evaluation Error:**\n\n{str(e)}\n\n```\n{traceback.format_exc()}\n```"
            return None, error_msg, ""


# Global UI instance
ui_instance = AgentUI()


async def initialize_agent_async():
    """Initialize the agent asynchronously."""
    try:
        print("Initializing agent...")
        agent = DocumentAgent()
        await agent.connect_mcp_servers()
        ui_instance.set_agent(agent)
        print("✓ Agent initialized successfully!")
        return True
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
        ui_instance.init_error = error_msg
        print(f"✗ Error initializing agent: {e}")
        traceback.print_exc()
        return False


def create_ui():
    """Create and configure the Gradio interface."""

    with gr.Blocks(title="Document Q&A Agent") as demo:

        gr.Markdown(
            """
            # 🤖 Document Question Answering Agent

            Ask questions about your documents. The agent will search for relevant information
            and analyze any images found in the documents.
            """
        )

        with gr.Tabs():
            # Chat Tab
            with gr.Tab("💬 Chat"):
                create_chat_tab()

            # Evaluation Tab
            with gr.Tab("📊 Evaluation"):
                create_evaluation_tab()

    return demo


def create_chat_tab():
    """Create the chat interface tab."""
    with gr.Row():
        with gr.Column(scale=2):
            # Chat interface
            chatbot = gr.Chatbot(
                label="Conversation",
                height=500,
            )

            with gr.Row():
                question_input = gr.Textbox(
                    label="Your Question",
                    placeholder="Ask a question about your documents...",
                    lines=2,
                    scale=4,
                )
                submit_btn = gr.Button("Ask", variant="primary", scale=1)

            with gr.Row():
                clear_btn = gr.Button("Clear History")

            # Examples
            gr.Examples(
                examples=[
                    "What documents do you have about Q4 results?",
                    "Search for architecture diagrams and describe what you find",
                    "Find the latest product documentation",
                    "What information is in the images from the quarterly report?",
                ],
                inputs=question_input,
                label="Example Questions",
            )

        with gr.Column(scale=1):
            # Tool calls panel
            tool_calls_display = gr.Markdown(
                value="No tool calls yet.",
                label="Tool Activity"
            )

            # Image gallery
            with gr.Accordion("Images Used", open=True):
                image_gallery = gr.Gallery(
                    label="Images analyzed in this conversation",
                )

            # Configuration info
            with gr.Accordion("Configuration", open=False):
                config_display = gr.Markdown(
                    value=ui_instance.get_config_info()
                )
                refresh_config_btn = gr.Button("Refresh Config")

            # Status panel
            with gr.Accordion("System Status", open=True):
                status_display = gr.Markdown(
                    value=ui_instance.get_status()
                )

    # Event handlers
    def submit_question(question, history):
        """Handle question submission."""
        if not question.strip():
            return history, "No tool calls yet.", []

        # Process question
        updated_history, tool_calls, images = ui_instance.ask_question(question, history)

        return updated_history, tool_calls, images

    submit_btn.click(
        fn=submit_question,
        inputs=[question_input, chatbot],
        outputs=[chatbot, tool_calls_display, image_gallery],
    ).then(
        fn=lambda: "",
        outputs=question_input,
    )

    question_input.submit(
        fn=submit_question,
        inputs=[question_input, chatbot],
        outputs=[chatbot, tool_calls_display, image_gallery],
    ).then(
        fn=lambda: "",
        outputs=question_input,
    )

    def clear_history():
        ui_instance.current_images = []
        return [], "No tool calls yet.", []

    clear_btn.click(
        fn=clear_history,
        outputs=[chatbot, tool_calls_display, image_gallery],
    )

    refresh_config_btn.click(
        fn=ui_instance.get_config_info,
        outputs=config_display,
    )


def create_evaluation_tab():
    """Create the evaluation interface tab."""
    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown(
                """
                ## DeepEval Evaluation

                Evaluate the agent's performance on a set of questions using the DeepEval framework.

                Upload a JSON file with evaluation questions or use the default `evaluation_questions.json`.
                """
            )

            with gr.Row():
                questions_file = gr.File(
                    label="Questions File (JSON)",
                    file_types=[".json"],
                    value="evaluation_questions.json",
                )

            with gr.Accordion("Evaluation Model Settings", open=False):
                gr.Markdown(
                    """
                    Configure which LLM to use for DeepEval metrics evaluation.
                    Use a cheaper/faster model here while keeping a premium model for your agent.
                    """
                )
                eval_provider = gr.Radio(
                    choices=["openai", "anthropic"],
                    value="openai",
                    label="Evaluation Provider",
                    info="Which LLM provider to use for evaluation metrics"
                )
                eval_model = gr.Textbox(
                    label="Evaluation Model",
                    placeholder="e.g., gpt-4o-mini or claude-3-5-haiku-20241022",
                    value="gpt-4o-mini",
                    info="Leave empty to use provider default"
                )

            with gr.Accordion("Rate Limiting", open=True):
                enable_rate_limit = gr.Checkbox(
                    label="Enable Rate Limiting",
                    value=True,
                    info="Limit API token usage to avoid rate limits"
                )
                tokens_per_minute = gr.Slider(
                    minimum=10000,
                    maximum=100000,
                    step=5000,
                    value=30000,
                    label="Tokens per Minute",
                    info="Maximum tokens to use per minute"
                )
                delay_slider = gr.Slider(
                    minimum=5,
                    maximum=30,
                    step=1,
                    value=10,
                    label="Delay Between Questions (seconds)",
                    info="Fixed delay to account for DeepEval API calls"
                )

            with gr.Row():
                run_eval_btn = gr.Button("🚀 Run Evaluation", variant="primary", size="lg")

            with gr.Row():
                summary_display = gr.Markdown(
                    value="Click 'Run Evaluation' to start.",
                    label="Summary"
                )

            with gr.Accordion("Detailed Results", open=False):
                detailed_display = gr.Markdown(
                    value="No evaluation run yet."
                )

        with gr.Column(scale=1):
            with gr.Accordion("Evaluation Metrics", open=True):
                gr.Markdown(
                    """
                    ### DeepEval Metrics

                    - **Faithfulness**: Is the answer grounded in the retrieved context?
                    - **Answer Relevancy**: How relevant is the answer to the question?
                    - **Contextual Precision**: Quality of retrieved context
                    - **Contextual Recall**: Was all relevant info retrieved?

                    **Score Range:** 0.0 - 1.0 (higher is better)
                    """
                )

            with gr.Accordion("Results Table", open=True):
                results_table = gr.Dataframe(
                    label="Scores by Question",
                    headers=["Question", "Faithfulness", "Answer Relevancy", "Context Precision", "Context Recall"],
                )

    # Event handler
    def run_evaluation_handler(questions_file, eval_prov, eval_mod, tokens_per_min, delay, enable_limit):
        """Handle evaluation button click."""
        results_df, summary, detailed = ui_instance.run_evaluation(
            questions_file,
            tokens_per_minute=int(tokens_per_min),
            delay_between_questions=float(delay),
            enable_rate_limiting=enable_limit,
            eval_provider=eval_prov,
            eval_model=eval_mod if eval_mod else None
        )

        if results_df is not None:
            # Format dataframe for display
            display_df = results_df.copy()
            # Round numeric columns
            for col in display_df.select_dtypes(include=['float64']).columns:
                display_df[col] = display_df[col].round(3)

            return summary, detailed, display_df
        else:
            # Error case
            return summary, detailed, None

    run_eval_btn.click(
        fn=run_evaluation_handler,
        inputs=[questions_file, eval_provider, eval_model, tokens_per_minute, delay_slider, enable_rate_limit],
        outputs=[summary_display, detailed_display, results_table],
    )


def main():
    """Main entry point."""
    print("=" * 60)
    print("Starting Document Q&A Agent UI...")
    print("=" * 60)
    print()

    # Initialize agent in main thread before starting UI
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        success = loop.run_until_complete(initialize_agent_async())
    finally:
        loop.close()

    if not success:
        print("\n⚠️  Agent initialization failed, but starting UI anyway.")
        print("Check the System Status panel in the UI for details.\n")

    # Create and launch UI
    print("\nLaunching UI...")
    demo = create_ui()

    # Launch configuration
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
