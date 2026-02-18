"""
Narrative Generator Service
=============================
Generates regulator-ready SAR narratives using LLM (Ollama or Claude)
with RAG-retrieved context. Falls back to template-based generation.
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# System prompt – enforces regulatory compliance in LLM output
# ------------------------------------------------------------------ #
SYSTEM_PROMPT = """You are a UK SAR (Suspicious Activity Report) narrative generation engine
used by compliance analysts at a regulated financial institution.

STRICT RULES YOU MUST FOLLOW:
1. Use ONLY the evidence and data provided. Do NOT fabricate or hallucinate any facts.
2. Write in formal, third-person, regulatory tone.
3. Present events in chronological order.
4. Reference specific transaction amounts, dates, and parties from the evidence.
5. Do NOT include internal system names, model scores, confidence levels, or reasoning IDs.
6. Do NOT include any discriminatory language based on race, religion, gender, ethnicity, or nationality.
7. If data is missing, write: "Information not available at time of submission."
8. Follow the SAR template structure exactly.
9. Cite relevant sections of the Proceeds of Crime Act 2002 (POCA) where applicable.
10. Include all typology indicators identified by the detection system.
11. DO NOT add sections not in the template.
12. DO NOT remove sections from the template.

OUTPUT FORMAT:
Return ONLY the completed SAR narrative. No preamble, no commentary, no markdown formatting.
"""


class NarrativeGenerator:
    """Generate SAR narrative using configurable LLM backend."""

    def generate(
        self,
        claim_object: Dict[str, Any],
        rag_context: Dict[str, Any],
        rule_result: Dict[str, Any],
        ml_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a SAR narrative.

        Returns
        -------
        dict with keys: narrative, llm_prompt, llm_provider, generated_at, is_fallback
        """
        user_prompt = self._build_prompt(claim_object, rag_context, rule_result, ml_result)
        full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"

        # Try LLM generation
        narrative = None
        llm_provider = "none"

        try:
            from backend.core.config import settings
            if settings.LLM_PROVIDER == "ollama":
                narrative = self._call_ollama(full_prompt, settings)
                llm_provider = f"ollama/{settings.OLLAMA_MODEL}"
            elif settings.LLM_PROVIDER == "claude":
                narrative = self._call_claude(full_prompt, settings)
                llm_provider = f"claude/{settings.CLAUDE_MODEL}"
        except Exception as e:
            logger.warning("LLM call failed: %s – using fallback template", e)

        is_fallback = narrative is None
        if is_fallback:
            narrative = self._generate_fallback(claim_object, rule_result, ml_result)
            llm_provider = "template_fallback"

        return {
            "narrative": narrative,
            "llm_prompt": full_prompt,
            "llm_provider": llm_provider,
            "generated_at": datetime.utcnow().isoformat(),
            "is_fallback": is_fallback,
        }

    # ------------------------------------------------------------ #
    # Prompt construction
    # ------------------------------------------------------------ #

    def _build_prompt(
        self,
        claim: Dict, rag: Dict, rules: Dict, ml: Dict,
    ) -> str:
        """Assemble the user prompt with all context."""
        # Template from RAG
        templates = rag.get("templates", [])
        template_text = templates[0]["content"] if templates else "Use standard SAR format."

        # Guidance from RAG
        guidelines = rag.get("guidelines", [])
        guidance_text = "\n".join(g["content"] for g in guidelines[:3]) if guidelines else ""

        # Similar cases
        sars = rag.get("sars", [])
        similar = "\n---\n".join(s["content"] for s in sars[:2]) if sars else "No similar cases available."

        # Evidence summary
        evidence_lines = []
        for ev in claim.get("evidence_summary", []):
            evidence_lines.append(f"• [{ev.get('rule', '')}] {ev.get('reasoning', '')}")
            for e in ev.get("evidence", []):
                evidence_lines.append(f"  - {e}")

        # Customer info
        cust = claim.get("customer_id", "Unknown")
        agg = claim.get("aggregates", {})
        kyc = claim.get("kyc_flags", {})

        prompt = f"""
TEMPLATE:
{template_text}

GUIDANCE:
{guidance_text}

CASE DATA:
- Customer ID: {cust}
- Typologies detected: {', '.join(claim.get('typologies', []))}
- Risk score: {claim.get('risk_score', 0):.2f}
- Total credits: ₹{agg.get('total_credit', 0):,.0f}
- Total debits: ₹{agg.get('total_debit', 0):,.0f}
- Transaction count: {agg.get('total_transactions', 0)}
- Unique counterparties: {agg.get('unique_counterparties', 0)}
- Date range: {agg.get('date_range_days', 0)} days
- KYC risk rating: {kyc.get('risk_rating', 'unknown')}
- PEP status: {kyc.get('pep', False)}
- Sanctions match: {kyc.get('sanctions', False)}

EVIDENCE:
{chr(10).join(evidence_lines)}

SIMILAR CASES:
{similar}

Generate the SAR narrative now, filling in all template sections using the evidence above.
"""
        return prompt

    # ------------------------------------------------------------ #
    # LLM backends
    # ------------------------------------------------------------ #

    def _call_ollama(self, prompt: str, settings) -> Optional[str]:
        """Call local Ollama instance."""
        import requests

        url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": settings.LLM_TEMPERATURE},
        }
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()

    def _call_claude(self, prompt: str, settings) -> Optional[str]:
        """Call Anthropic Claude API."""
        import anthropic

        client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
        message = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=4096,
            temperature=settings.LLM_TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()

    # ------------------------------------------------------------ #
    # Template fallback
    # ------------------------------------------------------------ #

    def _generate_fallback(
        self, claim: Dict, rules: Dict, ml: Dict,
    ) -> str:
        """Generate narrative from template when LLM is unavailable."""
        cust = claim.get("customer_id", "Unknown Subject")
        agg = claim.get("aggregates", {})
        typologies = claim.get("typologies", [])
        kyc = claim.get("kyc_flags", {})

        triggered = [r for r in rules.get("triggered_rules", []) if r.get("triggered")]
        evidence_text = ""
        for r in triggered:
            evidence_text += f"\n• {r.get('rule_name', '')}: {r.get('reasoning', '')}"
            for e in r.get("evidence", []):
                evidence_text += f"\n  - {e}"

        poca_section = ""
        if "structuring" in typologies or "layering" in typologies:
            poca_section = (
                "\n\nRelevant Legislation:\n"
                "This activity may constitute an offence under Section 327 (Concealing criminal property), "
                "Section 328 (Arrangements facilitating acquisition, retention, use or control of criminal property), "
                "or Section 329 (Acquisition, use and possession of criminal property) of the "
                "Proceeds of Crime Act 2002 (POCA)."
            )

        narrative = f"""SUSPICIOUS ACTIVITY REPORT

1. SUBJECT INFORMATION
   Customer ID: {cust}
   KYC Risk Rating: {kyc.get('risk_rating', 'N/A')}
   PEP Status: {'Yes' if kyc.get('pep') else 'No'}
   Sanctions Match: {'Yes' if kyc.get('sanctions') else 'No'}

2. SUSPICIOUS ACTIVITY DESCRIPTION
   a. Nature of Suspicious Activity:
      The following typologies have been identified: {', '.join(typologies) if typologies else 'General suspicious activity'}.

   b. Accounts and Transactions Involved:
      Total transactions: {agg.get('total_transactions', 0)}
      Total credits: ₹{agg.get('total_credit', 0):,.0f}
      Total debits: ₹{agg.get('total_debit', 0):,.0f}
      Unique counterparties: {agg.get('unique_counterparties', 0)}
      Transaction period: {agg.get('date_range_days', 0)} days

   c. Detection Summary:
      Composite risk score: {claim.get('risk_score', 0):.2f}
      ML confidence: {ml.get('ml_confidence', 0):.2f}
      Risk category: {ml.get('risk_category', 'Unknown')}

3. NARRATIVE
   The institution's monitoring systems identified suspicious financial activity associated with
   customer {cust}. During the observation period of {agg.get('date_range_days', 0)} days,
   the customer's accounts received ₹{agg.get('total_credit', 0):,.0f} in credits from
   {agg.get('unique_counterparties', 0)} unique counterparties. Subsequently,
   ₹{agg.get('total_debit', 0):,.0f} was debited from the accounts.

   The volume and pattern of transactions are inconsistent with the customer's declared profile
   and trigger the following concerns:
{evidence_text}

4. SUPPORTING EVIDENCE
   Rules triggered: {len(triggered)} of {len(rules.get('triggered_rules', []))} evaluated
   Typologies: {', '.join(typologies)}
{poca_section}

5. RECOMMENDATION
   Based on the analysis, this activity warrants further investigation and regulatory reporting.
   The case has been assigned a risk category of {ml.get('risk_category', 'Unknown')}.

[NOTICE: This narrative was generated using a template fallback. LLM-based generation was unavailable.]
"""
        return narrative
