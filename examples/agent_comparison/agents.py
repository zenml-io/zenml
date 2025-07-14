"""Agent Architecture Implementations.

This module contains the implementation of different agent architectures
for customer service query processing.
"""

import random
import time
from typing import Any, List, Optional, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from llm_utils import call_llm, should_use_real_llm
from materializers.prompt import Prompt


# LangGraph State Definition
class CustomerServiceState(TypedDict):
    """State definition for LangGraph customer service workflow."""

    messages: List[BaseMessage]
    query_type: str
    confidence: float
    response_text: str


class AgentResponse:
    """Response from an agent with metadata."""

    def __init__(
        self, text: str, latency_ms: float, confidence: float, tokens_used: int
    ):
        """Initialize agent response.

        Args:
            text: Response text from the agent
            latency_ms: Response time in milliseconds
            confidence: Confidence score (0-1)
            tokens_used: Number of tokens consumed
        """
        self.text = text
        self.latency_ms = latency_ms
        self.confidence = confidence
        self.tokens_used = tokens_used


class BaseAgent:
    """Base class for all agent architectures."""

    def __init__(self, name: str, prompts: Optional[List[Prompt]] = None):
        """Initialize base agent.

        Args:
            name: Name of the agent architecture
            prompts: List of Prompt objects loaded as ZenML artifacts
        """
        self.name = name
        self.prompts = {p.name: p for p in (prompts or [])}

    def process_query(self, query: str) -> AgentResponse:
        """Process a single query and return response with metadata.

        Args:
            query: Customer service query text

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError


class SingleAgentRAG(BaseAgent):
    """Simple RAG agent that handles all queries with one approach."""

    def __init__(self, prompts: Optional[List[Prompt]] = None) -> None:
        """Initialize SingleAgentRAG with knowledge base.

        Args:
            prompts: Optional list of Prompt objects loaded as ZenML artifacts
        """
        super().__init__("SingleAgentRAG", prompts)
        self.knowledge_base = {
            "return": "Items can be returned within 30 days with original receipt.",
            "refund": "Refunds are processed within 5-7 business days to original payment method.",
            "shipping": "Free shipping on orders over $50, otherwise $5.99 flat rate.",
            "support": "Customer support available 24/7 via chat, email, or phone.",
            "warranty": "All products come with 1-year manufacturer warranty.",
        }

    def process_query(self, query: str) -> AgentResponse:
        """Process query using LLM or simple keyword matching fallback.

        Args:
            query: Customer service query text

        Returns:
            AgentResponse with generated response and metadata
        """
        start_time = time.time()

        if should_use_real_llm():
            # Use real LLM for customer service response
            knowledge_context = "\n".join(
                [f"{k}: {v}" for k, v in self.knowledge_base.items()]
            )
            # Use loaded prompt template
            prompt_obj = self.prompts.get("single_agent_rag")
            if prompt_obj:
                prompt = prompt_obj.format(
                    knowledge_context=knowledge_context, query=query
                )
            else:
                # Fallback prompt
                prompt = f"You are a helpful customer service agent. Use this knowledge base to answer customer questions:\n\nKnowledge Base:\n{knowledge_context}\n\nCustomer Question: {query}\n\nProvide a helpful, professional response:"

            response_text = call_llm(
                prompt,
                model="gpt-3.5-turbo",
                metadata={
                    "agent_type": "SingleAgentRAG",
                    "query_length": len(query),
                    "knowledge_categories": list(self.knowledge_base.keys()),
                },
            )
            confidence = random.uniform(
                0.8, 0.95
            )  # Higher confidence for real LLM
            # Note: This is a rough approximation. For accurate token counting, use a tokenizer]
            #  like tiktoken or the tokenizer from the model provider
            tokens_used = len(prompt.split()) + len(response_text.split())
        else:
            # Fallback to mock keyword matching
            time.sleep(random.uniform(0.1, 0.3))  # Simulate processing time

            query_lower = query.lower()
            response_text = "I'd be happy to help you with that! "

            if "return" in query_lower:
                response_text += self.knowledge_base["return"]
            elif "refund" in query_lower:
                response_text += self.knowledge_base["refund"]
            elif "shipping" in query_lower or "ship" in query_lower:
                response_text += self.knowledge_base["shipping"]
            elif "warranty" in query_lower or "guarantee" in query_lower:
                response_text += self.knowledge_base["warranty"]
            else:
                response_text += "Let me connect you with a specialist who can help with your specific question."

            confidence = random.uniform(0.7, 0.9)
            tokens_used = random.randint(50, 150)

        latency_ms = (time.time() - start_time) * 1000

        return AgentResponse(
            text=response_text,
            latency_ms=latency_ms,
            confidence=confidence,
            tokens_used=tokens_used,
        )

    def get_graph_visualization(self) -> str:
        """Get a simple text representation of the SingleAgentRAG architecture.

        Returns:
            Text representation of the SingleAgentRAG workflow structure
        """
        return """
SingleAgentRAG Architecture:

INPUT (Customer Query) → RAG Knowledge Base Lookup → LLM/Fallback Response → OUTPUT

Architecture Details:
- Single unified approach for all query types
- Uses predefined knowledge base with 5 categories: return, refund, shipping, support, warranty
- LLM generates responses using knowledge context, or falls back to keyword matching
- No query routing or specialization - one size fits all

Knowledge Base Categories:
• return: Return policy information
• refund: Refund processing details  
• shipping: Shipping costs and policies
• support: Customer support availability
• warranty: Product warranty information
"""

    def get_mermaid_diagram(self) -> str:
        """Get a Mermaid diagram representation of the SingleAgentRAG workflow.

        Returns:
            HTML string containing interactive Mermaid diagram of the workflow
        """
        return """
<!DOCTYPE html>
<html>
<head>
    <title>SingleAgentRAG Architecture</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head>
<body>
    <div class="mermaid">
        graph TD
            A[Customer Query] --> B[Knowledge Base Lookup]
            B --> C{LLM Available?}
            C -->|Yes| D[LLM Processing]
            C -->|No| E[Keyword Matching]
            D --> F[Generate Response]
            E --> F
            F --> G[Customer Response]

            B[Knowledge Base Lookup<br/>🔍 Search across 5 categories:<br/>returns, refunds, shipping,<br/>support, warranty]
            D[LLM Processing<br/>🤖 Use prompt template<br/>with knowledge context]
            E[Keyword Matching<br/>📝 Simple fallback logic<br/>based on query keywords]
            F[Generate Response<br/>💬 Unified response<br/>regardless of query type]

            style A fill:#e1f5fe
            style G fill:#e8f5e8
            style B fill:#fff3e0
            style C fill:#f3e5f5
            style D fill:#e0f2f1
            style E fill:#ffebee
            style F fill:#fff8e1
    </div>
    <script>
        mermaid.initialize({ startOnLoad: true });
    </script>
</body>
</html>
"""


class MultiSpecialistAgents(BaseAgent):
    """Multiple specialized agents for different query types."""

    def __init__(self, prompts: Optional[List[Prompt]] = None) -> None:
        """Initialize MultiSpecialistAgents with specialist routing.

        Args:
            prompts: Optional list of Prompt objects loaded as ZenML artifacts
        """
        super().__init__("MultiSpecialistAgents", prompts)
        self.specialists = {
            "returns": "Returns Specialist: I handle all return and exchange requests.",
            "billing": "Billing Specialist: I can help with payment and billing questions.",
            "technical": "Technical Support: I assist with product setup and troubleshooting.",
            "general": "Customer Service: I'm here to help with general questions.",
        }

    def _route_query(self, query: str) -> str:
        """Route query to appropriate specialist.

        Args:
            query: Customer service query text to route

        Returns:
            str: Specialist category: 'returns', 'billing', 'technical', or 'general'
        """
        query_lower = query.lower()

        if any(
            word in query_lower for word in ["return", "exchange", "refund"]
        ):
            return "returns"
        elif any(
            word in query_lower
            for word in ["payment", "billing", "charge", "price"]
        ):
            return "billing"
        elif any(
            word in query_lower
            for word in ["setup", "install", "technical", "broken"]
        ):
            return "technical"
        else:
            return "general"

    def process_query(self, query: str) -> AgentResponse:
        """Process query using specialist routing with LLM or mock responses.

        Args:
            query: Customer service query text

        Returns:
            AgentResponse with generated response and metadata
        """
        start_time = time.time()

        specialist = self._route_query(query)

        if should_use_real_llm():
            # Use loaded specialist prompts
            specialist_prompt_obj = self.prompts.get(
                f"specialist_{specialist}"
            )
            if specialist_prompt_obj:
                prompt = specialist_prompt_obj.format(query=query)
            else:
                # Fallback prompts
                fallback_prompts = {
                    "returns": "You are a Returns Specialist. Help customers with returns, exchanges, and refunds professionally.\n\nCustomer Question: {query}\n\nProvide a helpful, specific response for this returns inquiry:",
                    "billing": "You are a Billing Specialist. Help customers with payment issues, billing questions, and account management.\n\nCustomer Question: {query}\n\nProvide a helpful, specific response for this billing inquiry:",
                    "technical": "You are a Technical Support Specialist. Help customers with product setup, troubleshooting, and technical issues.\n\nCustomer Question: {query}\n\nProvide a helpful, specific response for this technical inquiry:",
                    "general": "You are a General Customer Service Agent. Help customers with general questions and direct them to specialists when needed.\n\nCustomer Question: {query}\n\nProvide a helpful, specific response for this general inquiry:",
                }
                prompt = fallback_prompts[specialist].format(query=query)

            response_text = call_llm(
                prompt,
                model="gpt-3.5-turbo",
                metadata={
                    "agent_type": "MultiSpecialistAgents",
                    "specialist": specialist,
                    "query_length": len(query),
                    "routing_decision": specialist,
                },
            )
            confidence = random.uniform(
                0.85, 0.98
            )  # Higher confidence for specialized LLM
            # Note: This is a rough approximation. For accurate token counting, use a tokenizer]
            #  like tiktoken or the tokenizer from the model provider
            tokens_used = len(prompt.split()) + len(response_text.split())
        else:
            # Fallback to mock specialist responses
            time.sleep(
                random.uniform(0.15, 0.4)
            )  # Simulate routing and processing time

            base_response = self.specialists[specialist]

            # Add specific responses based on specialist
            if specialist == "returns":
                response_text = f"{base_response} Items can be returned within 30 days with receipt. Would you like me to start a return for you?"
            elif specialist == "billing":
                response_text = f"{base_response} I can help you review your account, process refunds, or update payment methods."
            elif specialist == "technical":
                response_text = f"{base_response} Let me walk you through the troubleshooting steps for your issue."
            else:
                response_text = f"{base_response} I can direct you to the right specialist or answer general questions about our policies."

            confidence = random.uniform(0.8, 0.95)
            tokens_used = random.randint(80, 200)

        latency_ms = (time.time() - start_time) * 1000

        return AgentResponse(
            text=response_text,
            latency_ms=latency_ms,
            confidence=confidence,
            tokens_used=tokens_used,
        )

    def get_graph_visualization(self) -> str:
        """Get a simple text representation of the MultiSpecialistAgents architecture.

        Returns:
            Text representation of the MultiSpecialistAgents workflow structure
        """
        return """
MultiSpecialistAgents Architecture:

INPUT (Customer Query) → Intent Router → Specialist Agent → LLM/Fallback Response → OUTPUT

Architecture Details:
- Multi-agent system with specialized experts
- Query routing based on keyword analysis
- Each specialist has domain expertise and specialized prompts
- Higher confidence due to specialization

Routing Logic:
• returns → Returns Specialist (return, exchange, refund keywords)
• billing → Billing Specialist (payment, billing, charge, price keywords)  
• technical → Technical Support (setup, install, technical, broken keywords)
• general → General Support (catch-all for other queries)

Specialist Capabilities:
• Returns Specialist: Handles returns, exchanges, refunds
• Billing Specialist: Payment issues, billing questions, account management
• Technical Support: Product setup, troubleshooting, technical issues
• General Support: Directs to other specialists, handles general inquiries
"""

    def get_mermaid_diagram(self) -> str:
        """Get a Mermaid diagram representation of the MultiSpecialistAgents workflow.

        Returns:
            HTML string containing interactive Mermaid diagram of the workflow
        """
        return """
<!DOCTYPE html>
<html>
<head>
    <title>MultiSpecialistAgents Architecture</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head>
<body>
    <div class="mermaid">
        graph TD
            A[Customer Query] --> B[Intent Router]
            B --> C{Query Classification}
            C -->|return, exchange, refund| D[Returns Specialist]
            C -->|payment, billing, charge| E[Billing Specialist]
            C -->|setup, install, technical| F[Technical Support]
            C -->|other queries| G[General Support]
            
            D --> H{LLM Available?}
            E --> I{LLM Available?}
            F --> J{LLM Available?}
            G --> K{LLM Available?}
            
            H -->|Yes| L[Returns LLM]
            H -->|No| M[Returns Fallback]
            I -->|Yes| N[Billing LLM]
            I -->|No| O[Billing Fallback]
            J -->|Yes| P[Technical LLM]
            J -->|No| Q[Technical Fallback]
            K -->|Yes| R[General LLM]
            K -->|No| S[General Fallback]
            
            L --> T[Customer Response]
            M --> T
            N --> T
            O --> T
            P --> T
            Q --> T
            R --> T
            S --> T

            B[Intent Router<br/>🎯 Keyword-based routing<br/>to appropriate specialist]
            D[Returns Specialist<br/>↩️ Handles returns,<br/>exchanges, refunds]
            E[Billing Specialist<br/>💳 Payment issues,<br/>billing questions]
            F[Technical Support<br/>🔧 Setup, troubleshooting,<br/>technical issues]
            G[General Support<br/>📞 General inquiries,<br/>routing assistance]

            style A fill:#e1f5fe
            style T fill:#e8f5e8
            style B fill:#fff3e0
            style C fill:#f3e5f5
            style D fill:#e0f2f1
            style E fill:#fff8e1
            style F fill:#fce4ec
            style G fill:#f1f8e9
    </div>
    <script>
        mermaid.initialize({ startOnLoad: true });
    </script>
</body>
</html>
"""


class LangGraphCustomerServiceAgent(BaseAgent):
    """LangGraph-based customer service agent with workflow visualization."""

    def __init__(self, prompts: Optional[List[Prompt]] = None) -> None:
        """Initialize LangGraph agent with workflow and knowledge base.

        Args:
            prompts: Optional list of Prompt objects loaded as ZenML artifacts
        """
        super().__init__("LangGraphCustomerServiceAgent", prompts)
        self.graph = self._build_graph()
        self.knowledge_base = {
            "return": "Items can be returned within 30 days with original receipt.",
            "refund": "Refunds are processed within 5-7 business days to original payment method.",
            "shipping": "Free shipping on orders over $50, otherwise $5.99 flat rate.",
            "support": "Customer support available 24/7 via chat, email, or phone.",
            "warranty": "All products come with 1-year manufacturer warranty.",
        }

    def _build_graph(self) -> Any:
        """Build the LangGraph workflow for customer service.

        Returns:
            Compiled StateGraph with customer service workflow nodes and edges
        """
        workflow = StateGraph(CustomerServiceState)

        # Add nodes
        workflow.add_node("analyze_query", self._analyze_query)
        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("validate_response", self._validate_response)

        # Add edges
        workflow.add_edge(START, "analyze_query")
        workflow.add_edge("analyze_query", "classify_intent")
        workflow.add_edge("classify_intent", "generate_response")
        workflow.add_edge("generate_response", "validate_response")
        workflow.add_edge("validate_response", END)

        return workflow.compile()

    def _analyze_query(
        self, state: CustomerServiceState
    ) -> CustomerServiceState:
        """Analyze the customer query.

        Args:
            state: Current customer service state with messages

        Returns:
            Updated state with confidence score based on query complexity
        """
        if state["messages"]:
            content = state["messages"][-1].content
            query = content if isinstance(content, str) else str(content)
            # Simple analysis
            complexity = len(query.split())
            state["confidence"] = 0.9 if complexity < 10 else 0.8
        return state

    def _classify_intent(
        self, state: CustomerServiceState
    ) -> CustomerServiceState:
        """Classify the customer's intent.

        Args:
            state: Current customer service state with messages

        Returns:
            Updated state with classified query_type (returns, billing, shipping, warranty, or general)
        """
        if state["messages"]:
            content = state["messages"][-1].content
            query = (
                content if isinstance(content, str) else str(content)
            ).lower()

            if any(word in query for word in ["return", "exchange", "refund"]):
                state["query_type"] = "returns"
            elif any(
                word in query for word in ["payment", "billing", "charge"]
            ):
                state["query_type"] = "billing"
            elif any(
                word in query for word in ["shipping", "delivery", "ship"]
            ):
                state["query_type"] = "shipping"
            elif any(
                word in query for word in ["warranty", "guarantee", "broken"]
            ):
                state["query_type"] = "warranty"
            else:
                state["query_type"] = "general"
        return state

    def _generate_response(
        self, state: CustomerServiceState
    ) -> CustomerServiceState:
        """Generate a response based on the classified intent using LLM or fallback.

        Args:
            state: Current customer service state with classified query_type

        Returns:
            Updated state with generated response_text
        """
        query_type = state.get("query_type", "general")
        query = state["messages"][-1].content if state["messages"] else ""

        if should_use_real_llm():
            # Use real LLM for response generation in LangGraph workflow
            knowledge_context = ""
            if query_type in self.knowledge_base:
                knowledge_context = (
                    f"Relevant knowledge: {self.knowledge_base[query_type]}"
                )

            # Use loaded LangGraph workflow prompt
            prompt_obj = self.prompts.get("langgraph_workflow")
            if prompt_obj:
                prompt = prompt_obj.format(
                    query_type=query_type,
                    knowledge_context=knowledge_context,
                    query=query,
                )
            else:
                # Fallback prompt
                prompt = f"You are a customer service agent in a structured workflow. \nYou have analyzed this query and classified it as: {query_type}\n\n{knowledge_context}\n\nCustomer Question: {query}\n\nGenerate a helpful, professional response. Be specific and actionable:"

            response = call_llm(
                prompt,
                model="gpt-3.5-turbo",
                metadata={
                    "agent_type": "LangGraphCustomerServiceAgent",
                    "query_type": query_type,
                    "workflow_step": "generate_response",
                    "query_length": len(str(query)),
                },
            )
        else:
            # Fallback to mock response generation
            if query_type in self.knowledge_base:
                base_response = self.knowledge_base[query_type]
                response = f"I understand you have a {query_type} question. {base_response} Is there anything specific about this I can help clarify?"
            else:
                response = "I'm here to help you with your question. Let me connect you with the right specialist who can provide detailed assistance."

        state["response_text"] = response
        return state

    def _validate_response(
        self, state: CustomerServiceState
    ) -> CustomerServiceState:
        """Validate and finalize the response.

        Args:
            state: Current customer service state with response_text

        Returns:
            Updated state with validated response_text and adjusted confidence
        """
        # Simple validation - ensure response is not empty and has reasonable length
        if len(state["response_text"]) < 20:
            state["response_text"] = (
                "I apologize, but I need more information to provide you with the best assistance. Could you please provide more details about your request?"
            )
            state["confidence"] = 0.6
        elif len(state["response_text"]) > 500:
            state["response_text"] = state["response_text"][:500] + "..."
            state["confidence"] = max(0.7, state["confidence"] - 0.1)

        return state

    def process_query(self, query: str) -> AgentResponse:
        """Process a query through the LangGraph workflow.

        Args:
            query: Customer service query text

        Returns:
            AgentResponse with generated response and metadata
        """
        start_time = time.time()

        # Initialize state
        initial_state = CustomerServiceState(
            messages=[HumanMessage(content=query)],
            query_type="",
            confidence=0.8,
            response_text="",
        )

        # Run through the graph
        final_state = self.graph.invoke(initial_state)

        latency_ms = (time.time() - start_time) * 1000

        return AgentResponse(
            text=final_state["response_text"],
            latency_ms=latency_ms,
            confidence=final_state["confidence"],
            tokens_used=random.randint(80, 180),  # Simulated for demo
        )

    def get_graph_visualization(self) -> str:
        """Get a simple text representation of the graph structure.

        Returns:
            Text representation of the LangGraph workflow structure
        """
        return """
LangGraph Customer Service Agent Workflow:

START → analyze_query → classify_intent → generate_response → validate_response → END

Node Details:
- analyze_query: Analyzes query complexity and sets initial confidence
- classify_intent: Classifies into returns, billing, shipping, warranty, or general
- generate_response: Generates appropriate response based on intent
- validate_response: Validates response quality and adjusts confidence
"""

    def get_mermaid_diagram(self) -> str:
        """Get a Mermaid diagram representation of the workflow.

        Returns:
            HTML string containing interactive Mermaid diagram of the workflow
        """
        return """
<!DOCTYPE html>
<html>
<head>
    <title>LangGraph Customer Service Agent Workflow</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head>
<body>
    <div class="mermaid">
        graph TD
            A[START] --> B[analyze_query]
            B --> C[classify_intent]
            C --> D[generate_response]
            D --> E[validate_response]
            E --> F[END]

            B[analyze_query<br/>📊 Analyze query complexity<br/>Set initial confidence]
            C[classify_intent<br/>🏷️ Classify into:<br/>returns, billing, shipping,<br/>warranty, or general]
            D[generate_response<br/>💬 Generate response<br/>based on intent]
            E[validate_response<br/>✅ Validate quality<br/>Adjust confidence]

            style A fill:#e1f5fe
            style F fill:#e8f5e8
            style B fill:#fff3e0
            style C fill:#f3e5f5
            style D fill:#e0f2f1
            style E fill:#fff8e1
    </div>
    <script>
        mermaid.initialize({ startOnLoad: true });
    </script>
</body>
</html>
"""
