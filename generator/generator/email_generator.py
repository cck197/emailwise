import os

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from .settings import get_settings

GROQ_MODEL_NAME = os.environ.get("GROQ_MODEL_NAME", "llama3-70b-8192")
OPENAI_MODEL_NAME = os.environ.get("OPENAI_MODEL_NAME", "gpt-4o")
ANTHROPIC_MODEL_NAME = os.environ.get("ANTHROPIC_MODEL_NAME", "claude-3-opus-20240229")


SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "You are legendary copywriter Gary C Halbert, and you're helping a store owner write copy that converts.",
)

LLAMA3_AVOID_EXTRA_CRUFT = os.environ.get(
    "LLAMA3_AVOID_EXTRA_CRUFT",
    """Avoid starting your responses with 'Here is the' or 'Here's the'. Provide the answer and nothing else.""",
)

STYLE_ATTRS = os.environ.get(
    "STYLE_ATTRS",
    """
- Tone: The attitude conveyed by the writer towards the subject or audience.
- Mood: The overall emotional atmosphere perceived by the reader.
- Pace: The speed at which the story or content progresses.
- Style: The distinctive way in which the author uses language and structure.
- Voice: The unique personality the writer brings to the text, distinct from other authors.
- Diction: The choice of words and their connotations, which influence the tone and readability.
- Syntax: The arrangement of words and phrases to create well-formed sentences, affecting clarity and pace.
- Imagery: The use of descriptive or figurative language to create vivid pictures in the reader's mind.
- Theme: The underlying message or main idea the writer wishes to convey.
- Perspective: The point of view from which the story is told, influencing how information is presented to the reader.
""",
)

COPY_INSTRUCTIONS = os.environ.get(
    "COPY_INSTRUCTIONS",
    """
use the PASTOR method 

'PASTOR' stands for problem, amplify, story, transformation, offer, response.

work through each step below and include each in the output but without the name of the step

1.  Problem: Identify your audience's pain points and challenges.

2. Amplify: Amplify the consequences of not addressing the problem.

3. Story: Share a relatable story or example that illustrates the problem.

4. Transformation: Offer a solution that transforms the situation.

5. Offer: Present your product or service as the key to achieving the transformation.

6. Response: End with a clear call-to-action that encourages people to take the next step.
""",
)

SALT_INSTRUCTIONS = os.environ.get(
    "SALT_INSTRUCTIONS",
    """
Use the salt below delimited by triple backticks to generate unique content for the product description.
""",
)

TONE_INSTRUCTIONS = os.environ.get(
    "TONE_INSTRUCTIONS",
    "List the tone qualities for the text delimited by triple backticks below using the list.",
)

LIKENESS_INSTRUCTIONS = os.environ.get(
    "LIKENESS_INSTRUCTIONS",
    """
The email should have similar tone qualities to those listed below. 
The degree of likeness is a five point scale from 1 to 5:
1: Not at all
2: Very little
3: Somewhat
4: Quite a bit
5: Very much
""",
)

FINAL_PROMPT = os.environ.get(
    "FINAL_PROMPT",
    """
Write a brief (no more than 500 words) sales email for the product delimited by triple backticks below.
Start the email with a catchy subject line.
""",
)

default_chat = ChatGroq(temperature=0, model_name=GROQ_MODEL_NAME)


def get_chat(settings):
    kwargs = {"api_key": settings.lLMKey}
    chat_map = {
        "Groq": ChatGroq(temperature=0, model_name=GROQ_MODEL_NAME, **kwargs),
        "OpenAI": ChatOpenAI(temperature=0, model_name=OPENAI_MODEL_NAME, **kwargs),
        "Anthropic": ChatAnthropic(
            temperature=0, model_name=ANTHROPIC_MODEL_NAME, **kwargs
        ),
    }
    return chat_map.get(settings.lLMProvider.name, default_chat)


async def get_email_generator(db, id):
    return await db.emailgenerator.find_first(where={"id": id})


async def save_email(db, name, html, text, email_generator):
    return await db.email.create(
        data={
            "shop": email_generator.shop,
            "emailGeneratorId": email_generator.id,
            "name": name,
            "html": html,
            "text": text,
        }
    )


async def get_sample_email(db, shop):
    return await db.email.find_first(
        order={
            "createdAt": "desc",
        },
        where={"shop": shop, "emailGeneratorId": None},
    )


def clean_email(email, chat=default_chat):
    system = f"""Your job is to return the text formatted nicely with no special
    characters or multiple spaces or blank lines. {LLAMA3_AVOID_EXTRA_CRUFT}"""
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", "{text}")])
    chain = prompt | chat
    return chain.invoke({"text": email.text})


def get_email_tone(email, chat=default_chat):
    cleaned_email = clean_email(email, chat).content
    system = f"""{TONE_INSTRUCTIONS} {LLAMA3_AVOID_EXTRA_CRUFT}"""
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", "{text}")])
    chain = prompt | chat
    return chain.invoke({"text": f"```{cleaned_email}```\n{STYLE_ATTRS}"})


def get_product_copy_chain(tone, prod_desc, salt, likeness, chat=default_chat):
    system = f"""{SYSTEM_PROMPT} {LLAMA3_AVOID_EXTRA_CRUFT}"""
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", "{text}")])
    chain = prompt | chat

    return (
        chain,
        {
            "text": f"{FINAL_PROMPT}\n{COPY_INSTRUCTIONS}\n"
            f"{SALT_INSTRUCTIONS}\n\n%SALT%```{salt}```\n"
            f"%PROD%```{prod_desc}```\n"
            f"{LIKENESS_INSTRUCTIONS} %LIKENESS```{likeness}```\n{tone}"
        },
    )


async def generate_email(db, email_generator):
    settings = await get_settings(db, email_generator.shop)
    chat = get_chat(settings)
    print(f"{chat=}")
    sample_email = await get_sample_email(db, email_generator.shop)
    tone = get_email_tone(sample_email, chat=chat).content
    return get_product_copy_chain(
        tone,
        email_generator.productDescription,
        email_generator.salt,
        email_generator.likeness,
        chat=chat,
    )
