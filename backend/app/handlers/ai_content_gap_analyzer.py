from typing import Any, Dict, List, Optional

from app.config import get_config
from app.engine.emitter import EventEmitter
from app.engine.message_router import route
from app.procs.embeddings import EmbeddingModel

# from chat_server.services.support_data_client import SupportDataClient
from langchain_core.output_parsers import (JsonOutputParser,
                                           PydanticOutputParser)
from langchain_core.prompts.chat import ChatPromptTemplate
from pydantic import BaseModel, Field, confloat, conlist

from app.procs.semantic_search.q_search_engine import SemanticSearchEngine

# TODO: Move this to main and pass to the routes
from app.llms.ollama_client import OllamaClient


cfg = get_config()
data_dir = cfg.ai_assessment.data_dir


# TODO: Move this to main
llm_client = OllamaClient().llm

# -----------------------------------------------------------------------------
# TODO: Hard-Coded
# hard-coded
# -----------------------------------------------------------------------------
emb_cfg = cfg.ai_assessment.embedding
engine = SemanticSearchEngine(emb_cfg.collection_name)

# --------------------------------------------------------------------------
@route("SUPPORTWIZ_USER_REQS", "SUMMARY-SEMANTIC-SEARCH")
async def search_s_kbindex_by_context(
   ws, 
   client_id, 
   request, 
   manager
) -> Dict[str, Any]:
    """
    Semantic / similarity search on KB questions by context text.
    Optionally creates a cluster.
    """

    emitter = EventEmitter(websocket=ws)
    await emitter.info("💬 Connected (Context: SupportWiz)" )

    reqData = request.reqData
    
    if not reqData:     
        await emitter.error("🚩 Missing 'reqData' field")
        return

    # index_name = reqData.get("index_name", "") 
    QUERY = reqData.get("context", "") 
    COUNT = reqData.get("count", 10)

    if not all([QUERY, COUNT]):
        await emitter.error("🚩 The payload 'reqData must contain these: QUERY and COUNT'")
        return


    supportwiz_response = engine.semantic_summary(QUERY, COUNT)

    payload = {
        "reqType": request.reqType,
        "reqSubType": request.reqSubType,
    }

    if isinstance(supportwiz_response, dict):
        payload.update(supportwiz_response)
    elif isinstance(supportwiz_response, list):
        payload["data"] = supportwiz_response
    else:
        payload["data"] = supportwiz_response

 
    await emitter.info("🧱 Summaries:", 
            payload=payload
    )



# ---------------------------------------------------
#   REQUEST 2:
# ---------------------------------------------------
@route("SUPPORTWIZ_USER_REQS", "USER-ANSWER-GAP-ANALYSIS")
async def answer_gap_analysis(ws, client_id, request, manager):
           
    emitter = EventEmitter(websocket=ws)

    reqData = request.reqData
    
    if not reqData:     
        await emitter.error("🚩 Missing 'reqData' field")
        return

    # category = reqData.get("category", "") 
    customer_id =reqData.get("customer_id", "")  
    index_name = reqData.get("index_name", "") 
    question = reqData.get("question", "") 
    question_id = reqData.get("question_id", "") 
    user_answer = reqData.get("user_answer", "") 


    if not all([index_name, question, user_answer]):
        await emitter.error("🚩 The payload 'reqData must contain these: question, index_name, user_answer")
        return

    # -----------------------------------------------------------------------------------
    # Step 1: Fetch Data
    # -----------------------------------------------------------------------------------

    supportwiz_response = engine.semantic_summary(question, 10)



    """
      {
        payload: {
        "summaries": [
              {
                "text": "This cluster explores the factors contributing to failure rates ...",
                "id": "278c4447c7eef12e5eebf512bad1d5b7481bb2cf"
              },
              ...
              ]
          }
      }
    """


    # -----------------------------------------------------------------------------------
    # Step 2: Synthesize
    # -----------------------------------------------------------------------------------

    payload = {}

    if isinstance(supportwiz_response, dict):
        payload.update(supportwiz_response)
    elif isinstance(supportwiz_response, list):
        payload["data"] = supportwiz_response
    else:
        payload["data"] = supportwiz_response


    def summaries_to_text(summaries: List[Dict[str, Any]]) -> str:
        return "\n\n".join(
                  f"""Document: {s.get('doc_id', 'N/A')}
          Type: {s.get('chunk_type', 'N/A')}
          Score: {round(s.get('score', 0), 3)}
          Section: {' > '.join(s.get('section_path', []))}

          Text:
          {s.get('text', '')}
          """.strip()
                  for s in summaries
                  if s.get("text")
              )

    summaries_text = summaries_to_text(payload["results"])


    # await emitter.info("🧱 Search Data Structure:", 
    #         payload=summaries_text
    #   )    


    # -----------------------------------------------------------------------------------
    # Step 3: Find Gap
    # -----------------------------------------------------------------------------------

    # Build the prompt (clean + deterministic)
    prompt = ChatPromptTemplate.from_template(
    """
    You are an enterprise knowledge synthesis and gap analysis assistant.

    Your task MUST be executed in TWO STRICTLY SEPARATED STEPS.

    ────────────────────────────────────────────────────────
    STEP 1 — AUTHORITATIVE SYNTHESIS
    ────────────────────────────────────────────────────────
    - Derive the correct and complete answer to the USER QUESTION.
    - Use ONLY the RETRIEVED CONTEXT provided.
    - Do NOT use prior knowledge, assumptions, or external information.
    - If the retrieved context is insufficient, explicitly state that limitation.
    - This synthesized answer will be treated as the reference truth.

    ────────────────────────────────────────────────────────
    STEP 2 — GAP ANALYSIS AGAINST USER ANSWER
    ────────────────────────────────────────────────────────
    - Compare the USER ANSWER strictly against the synthesized answer from STEP 1.
    - Identify ONLY what is missing, incomplete, unclear, or incorrect.
    - Do NOT restate the synthesized answer verbatim.
    - Do NOT evaluate tone, writing style, or intent.
    - Focus purely on factual, conceptual, or procedural gaps.
    - Frame gaps as constructive guidance for improvement.

    ────────────────────────────────────────────────────────
    GLOBAL RULES
    ────────────────────────────────────────────────────────
    - No speculation.
    - No hallucination.
    - No content outside the retrieved context.
    - Use precise, neutral, professional language.
    - Maintain clear traceability between synthesis and identified gaps.
    - Return ONLY valid JSON matching the provided schema.

    {format_instructions}

    ────────────────────────────────────────────────────────
    USER QUESTION:
    {question}

    QUESTION INTENT:
    {question_intent}

    ────────────────────────────────────────────────────────
    USER ANSWER:
    {user_answer}

    ────────────────────────────────────────────────────────
    RETRIEVED CONTEXT (Knowledge Base):
    {content}
    ────────────────────────────────────────────────────────
    """
    )

    # Assemble the chain
    parser = JsonOutputParser(pydantic_object=SynthesisGapOutput)

    chain = (
        prompt.partial(
            format_instructions=parser.get_format_instructions()
        )
        | llm_client
        | parser
    )


    ai_summary = chain.invoke({
        "content": summaries_text,
        "question": question,
        "user_answer": user_answer,
        "question_intent": "Evaluate implementation gaps between the user's answer and the authoritative synthesized answer derived from the knowledge base"
    })

  
    
    # always - reqType and reqSubType are inside the payload.
    payload = {
        "reqType": request.reqType,
        "reqSubType": request.reqSubType,
        "customer_id" : customer_id,
        "question_id": question_id,   
        "data": ai_summary
    }

    
    await emitter.info("🧱 Gap Analysis:", 
          payload=payload            
    )    



class SynthesisGapOutput(BaseModel):

    synthesized_summary: str = Field(
        description=(
            "Authoritative, concise answer synthesized strictly from the retrieved "
            "context. This represents the reference answer used for gap evaluation."
        )
    )

    key_themes: List[str] = Field(
        description=(
            "Distinct, high-level concepts explicitly present in the retrieved "
            "context and reflected in the synthesized_summary."
        ),
        min_items=1
    )

    user_gap: List[str] = Field(
        description=(
            "Concrete, factual gaps, omissions, or inaccuracies in the user answer "
            "when compared strictly against the synthesized_summary. "
            "Each item must describe a single, specific gap."
        )
    )

    insights: List[str] = Field(
        description=(
            "Actionable, improvement-oriented guidance that helps the user close "
            "the identified gaps. Each insight should directly correspond to one "
            "or more items in user_gap."
        )
    )

    match_score: confloat(ge=0.0, le=1.0) = Field(
        description=(
            "Numerical alignment score between the user answer and the synthesized_summary. "
            "0.0 indicates no meaningful alignment. "
            "1.0 indicates full alignment with no substantive gaps. "
            "Score must be derived solely from content coverage and correctness."
        )
    )
 

 

# @route("SUPPORTWIZ_USER_REQS", "QUESTION-SEMANTIC-SEARCH")
# async def search_q_kbindex_by_context(
#    ws, 
#    client_id, 
#    request, 
#    manager
# ) -> Dict[str, Any]:
#     """
#     Semantic / similarity search on KB questions by context text.
#     Optionally creates a cluster.
#     """

#     emitter = EventEmitter(websocket=ws)
#     await emitter.info("💬 Connected (Context: SupportWiz)" )

#     reqData = request.reqData
    
#     if not reqData:     
#         await emitter.error("🚩 Missing 'reqData' field")
#         return

#     index_name = reqData.get("index_name", "") 
#     context = reqData.get("context", "") 
#     count = reqData.get("count", 10)
#     create_cluster = reqData.get("create_cluster", False)  

#     if not all([index_name, context]):
#         await emitter.error("🚩 The payload 'reqData must contain these: context and index_name'")
#         return   
 
#     payload_to_support_wiz={
#               "reqType": request.reqType,
#               "reqSubType": request.reqSubType,
#               "reqData": {
#                 "index_name": index_name,
#                 "context": context,
#                 "count": count,
#                 "create_cluster": create_cluster
#               }
#           }

#     supportwiz_response =    await support_client.send_request(payload_to_support_wiz)


#     payload = {
#         "reqType": request.reqType,
#         "reqSubType": request.reqSubType,
#     }

#     if isinstance(supportwiz_response, dict):
#         payload.update(supportwiz_response)
#     elif isinstance(supportwiz_response, list):
#         payload["data"] = supportwiz_response
#     else:
#         payload["data"] = supportwiz_response

 
#     await emitter.info("🧱 Questions:", 
#             payload=payload
#     )
 
