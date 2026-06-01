from groq import Groq
from typing import List, Dict, Any

def get_ai_response(
    messages: List[Dict[str, str]], 
    api_key: str, 
    portfolio_context: Dict[str, Any]
) -> str:
    """
    Sends a chat conversation history to the Groq API (llama-3.1-8b-instant)
    with a rich, structurally injected system prompt containing full portfolio
    balances, active tax lots, sector weightings, dividends, and live business news.

    Args:
        messages (List[Dict]): Multi-turn conversation history (role: user/assistant).
        api_key (str): Secured Groq API Key.
        portfolio_context (Dict): Dict containing:
            - total_value (float)
            - total_cost (float)
            - unrealized_gain (float)
            - unrealized_pct (float)
            - active_holdings (List[Dict])
            - sector_weights (Dict[str, float])
            - dividends (List[Dict])
            - news_headlines (List[str])

    Returns:
        str: AI Analyst response in Markdown format.
    """
    if not api_key:
        return "⚠️ Error: Groq API Key is not configured. Please supply your key in the top-right Settings popover."

    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        return f"⚠️ Error initializing Groq client: {str(e)}"

    # 1. Structure the rich system context prompt
    holdings_str = ""
    for h in portfolio_context.get("active_holdings", []):
        holdings_str += (
            f"- **{h['ticker']}** ({h['name']}): "
            f"{h['shares']:.2f} shares | "
            f"Avg Cost: ${h['avg_cost']:.2f} | "
            f"Current Price: ${h['price']:.2f} | "
            f"Market Value: ${h['market_value']:.2f} | "
            f"Unrealized Gain: ${h['gain']:+,.2f} ({h['gain_pct']:+.2f}%)\n"
        )

    sectors_str = ""
    for sec, val in portfolio_context.get("sector_weights", {}).items():
        sectors_str += f"- **{sec}**: ${val:,.2f}\n"

    div_str = ""
    for d in portfolio_context.get("dividends", []):
        div_str += f"- **{d['ticker']}**: Yield {d['yield']} | Next Ex-Div Date: {d['date']}\n"

    news_str = ""
    for art in portfolio_context.get("news_headlines", []):
        news_str += f"- [{art['ticker']}] {art['title']} (Source: {art['publisher']})\n"

    system_prompt = f"""You are a professional Wall Street Stock Portfolio Analyst Agent and financial advisor.
Your goal is to provide institutional-grade, highly rigorous, and extremely actionable investment analysis to the user.

You have 100% real-time, accurate context about the user's personal portfolio. 
Here are the current portfolio metrics:
- **Total Portfolio Valuation**: ${portfolio_context.get('total_value', 0.0):,.2f}
- **Total Cost Basis**: ${portfolio_context.get('total_cost', 0.0):,.2f}
- **Total Unrealized Gains**: ${portfolio_context.get('unrealized_gain', 0.0):+,.2f} ({portfolio_context.get('unrealized_pct', 0.0):+.2f}%)
- **Total Realized Gains**: ${portfolio_context.get('realized_gain', 0.0):+,.2f}

Active Holdings & Tax Lots:
{holdings_str if holdings_str else "No active holdings."}

Sector Allocations:
{sectors_str if sectors_str else "No sector data."}

Fundamental Yields & Dividend Schedules:
{div_str if div_str else "No dividend schedules."}

Recent Business Headlines & RSS Feeds:
{news_str if news_str else "No recent news."}

---
CRITICAL INSTRUCTIONS FOR YOUR ANALYSIS:
1. **Always ground your claims in the exact figures provided above**. Do not make up numbers or reference stocks they do not own unless doing comparative analysis.
2. **Be specific and professional**: Analyze concentrations, capital allocations, and diversification risks. 
3. **Use Markdown formatting**: Use tables, bullet points, and bold text to present summaries beautifully.
4. **Disclaimers**: Always include a standard, professional, short financial disclaimer at the very end of your response stating that your insights are for educational purposes and do not constitute formal investment advice.
"""

    # 2. Package messages with the system prompt injected at the beginning
    api_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        chat_completion = client.chat.completions.create(
            messages=api_messages,
            model="llama-3.1-8b-instant",
            temperature=0.3, # low temperature for precise, fact-grounded financial advice
            max_tokens=1500
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ Groq API Error: Failed to generate response. Details: {str(e)}"
