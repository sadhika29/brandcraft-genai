import re
import logging
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException
from app.schemas import SentimentRequest, SentimentResponse, EmotionDetection
from app.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/api/sentiment", tags=["sentiment"])

logger = logging.getLogger(__name__)

STOPWORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having",
    "do", "does", "did", "doing",
    "a", "an", "the", "and", "but", "if", "or", "because",
    "as", "until", "while", "of", "at", "by", "for", "with",
    "about", "against", "between", "into", "through", "during",
    "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how",
    "all", "any", "both", "each", "few", "more", "most", "other",
    "some", "such", "no", "nor", "only", "own", "same", "so",
    "than", "too", "very", "can", "will", "just", "should", "now"
}

POSITIVE_WORDS = {
    "good": 2,
    "great": 3,
    "excellent": 4,
    "amazing": 4,
    "awesome": 4,
    "fantastic": 4,
    "wonderful": 4,
    "perfect": 4,
    "best": 4,
    "love": 4,
    "loved": 4,
    "lovely": 3,
    "happy": 3,
    "satisfied": 3,
    "satisfaction": 3,
    "helpful": 3,
    "friendly": 2,
    "fast": 2,
    "quick": 2,
    "easy": 2,
    "easier": 2,
    "beautiful": 3,
    "impressive": 3,
    "impressed": 3,
    "recommend": 3,
    "recommended": 3,
    "reliable": 3,
    "efficient": 3,
    "smooth": 3,
    "excellent": 4,
    "nice": 2,
    "cool": 2,
    "smart": 2,
    "useful": 2,
    "worth": 2,
    "value": 2,
    "success": 3,
    "successful": 3,
    "enjoy": 3,
    "enjoyed": 3,
    "delighted": 4,
    "pleasant": 3,
    "outstanding": 4,
    "superb": 4,
    "brilliant": 4,
    "fresh": 2,
    "innovative": 3,
    "innovation": 3,
    "responsive": 3,
    "professional": 3,
    "quality": 2,
    "strong": 2,
    "fastest": 3,
    "quickly": 2,
    "thank": 2,
    "thanks": 2,
    "grateful": 3,
    "glad": 3,
    "excited": 3,
    "thrilled": 4
}

NEGATIVE_WORDS = {
    "bad": 3,
    "worst": 5,
    "terrible": 5,
    "horrible": 5,
    "awful": 5,
    "hate": 4,
    "hated": 4,
    "angry": 4,
    "mad": 3,
    "frustrated": 4,
    "frustrating": 4,
    "poor": 3,
    "slow": 3,
    "crash": 4,
    "crashed": 4,
    "error": 3,
    "errors": 3,
    "issue": 2,
    "issues": 2,
    "bug": 3,
    "bugs": 3,
    "broken": 4,
    "broke": 4,
    "useless": 4,
    "garbage": 5,
    "fail": 4,
    "failed": 4,
    "failure": 4,
    "disappoint": 4,
    "disappointed": 4,
    "disappointing": 4,
    "regret": 4,
    "annoy": 3,
    "annoyed": 3,
    "annoying": 3,
    "pain": 3,
    "painful": 3,
    "difficult": 2,
    "difficulty": 2,
    "rude": 3,
    "delay": 3,
    "delayed": 3,
    "waste": 3,
    "wasted": 3,
    "dirty": 3,
    "dirt": 3,
    "stupid": 4,
    "expensive": 2,
    "costly": 2,
    "problem": 3,
    "problems": 3,
    "unhappy": 4,
    "unacceptable": 5,
    "unreliable": 4,
    "poorly": 3,
    "confusing": 2,
    "confused": 2,
    "mess": 3,
    "messy": 3,
    "dislike": 3,
    "disliked": 3,
    "refund": 2,
    "complaint": 3,
    "complain": 3,
    "complained": 3,
    "missing": 2,
    "lost": 2,
    "failures": 4
}

NEGATIONS = {
    "not",
    "never",
    "no",
    "neither",
    "nor",
    "hardly",
    "barely",
    "without",
    "isn't",
    "wasn't",
    "weren't",
    "aren't",
    "don't",
    "doesn't",
    "didn't",
    "can't",
    "cannot",
    "couldn't",
    "wouldn't",
    "shouldn't",
    "won't",
    "haven't",
    "hasn't",
    "hadn't"
}

INTENSIFIERS = {
    "very": 1.5,
    "really": 1.4,
    "extremely": 1.8,
    "absolutely": 2.0,
    "totally": 1.6,
    "completely": 1.7,
    "so": 1.3,
    "highly": 1.5,
    "incredibly": 1.8
}

POSITIVE_PHRASES = {
    "very good": 3,
    "very nice": 3,
    "really good": 3,
    "really great": 4,
    "highly recommend": 5,
    "love it": 5,
    "loved it": 5,
    "works perfectly": 5,
    "works great": 4,
    "very happy": 4,
    "very satisfied": 4,
    "excellent service": 5,
    "great service": 4,
    "good service": 3,
    "great experience": 4,
    "good experience": 3,
    "amazing experience": 5,
    "best experience": 5,
    "easy to use": 3,
    "user friendly": 3,
    "well designed": 3
}

NEGATIVE_PHRASES = {
    "very bad": 5,
    "very poor": 5,
    "really bad": 5,
    "really poor": 5,
    "very slow": 5,
    "really slow": 5,
    "extremely bad": 6,
    "extremely poor": 6,
    "hate it": 5,
    "hated it": 5,
    "does not work": 5,
    "doesn't work": 5,
    "not working": 5,
    "not good": 4,
    "not happy": 4,
    "not satisfied": 4,
    "not useful": 4,
    "not worth": 4,
    "waste of money": 5,
    "poor service": 4,
    "bad service": 5,
    "terrible service": 6,
    "bad experience": 5,
    "terrible experience": 6,
    "very disappointing": 5,
    "highly disappointing": 5,
    "customer service was terrible": 6,
    "doesn't help": 4,
    "not helpful": 4
}

EMOTION_WORDS = {
    "happy": {
        "happy", "glad", "joy", "smile", "delighted",
        "pleased", "love", "loved", "satisfied", "wonderful",
        "perfect", "enjoy", "enjoyed", "grateful"
    },
    "angry": {
        "angry", "mad", "rage", "furious", "hate",
        "hated", "terrible", "horrible", "garbage",
        "rude", "stupid", "unacceptable"
    },
    "excited": {
        "excited", "thrilled", "amazing", "awesome",
        "fantastic", "wow", "brilliant", "superb",
        "epic", "incredible"
    },
    "frustrated": {
        "frustrated", "frustrating", "slow", "broken",
        "bug", "bugs", "crash", "crashed", "error",
        "errors", "stuck", "failed", "failure",
        "delay", "delayed", "annoying", "annoyed"
    },
    "satisfied": {
        "satisfied", "satisfaction", "good", "great",
        "fine", "useful", "helpful", "works",
        "working", "recommend", "recommended",
        "reliable", "efficient", "quality"
    }
}


def tokenize(text: str):
    return re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", text.lower())


def phrase_score(text: str):
    score = 0

    for phrase, weight in POSITIVE_PHRASES.items():
        if phrase in text:
            score += weight

    for phrase, weight in NEGATIVE_PHRASES.items():
        if phrase in text:
            score -= weight

    return score


def analyze_lexicon_sentiment(text: str) -> SentimentResponse:
    logger.info("Using improved local lexicon sentiment engine.")

    clean_text = text.lower()
    words = tokenize(clean_text)

    if not words:
        return SentimentResponse(
            positive_percentage=33.3,
            negative_percentage=33.3,
            neutral_percentage=33.4,
            keywords=["service", "product", "experience"],
            emotions=EmotionDetection(
                happy=20.0,
                angry=10.0,
                excited=15.0,
                frustrated=15.0,
                satisfied=40.0
            )
        )

    positive_score = 0.0
    negative_score = 0.0

    emotion_scores = {
        "happy": 0.0,
        "angry": 0.0,
        "excited": 0.0,
        "frustrated": 0.0,
        "satisfied": 0.0
    }

    keyword_words = []

    i = 0

    while i < len(words):
        word = words[i]

        if word not in STOPWORDS and len(word) > 2:
            keyword_words.append(word)

        negated = False

        for j in range(max(0, i - 3), i):
            if words[j] in NEGATIONS:
                negated = True
                break

        intensity = 1.0

        for j in range(max(0, i - 2), i):
            if words[j] in INTENSIFIERS:
                intensity = INTENSIFIERS[words[j]]

        if word in POSITIVE_WORDS:
            weight = POSITIVE_WORDS[word] * intensity

            if negated:
                negative_score += weight
            else:
                positive_score += weight

        elif word in NEGATIVE_WORDS:
            weight = NEGATIVE_WORDS[word] * intensity

            if negated:
                positive_score += weight
            else:
                negative_score += weight

        for emotion, emotion_words in EMOTION_WORDS.items():
            if word in emotion_words:
                emotion_scores[emotion] += 1.0

        i += 1

    phrase = phrase_score(clean_text)

    if phrase > 0:
        positive_score += phrase

    elif phrase < 0:
        negative_score += abs(phrase)

    total_sentiment_score = positive_score + negative_score

    if total_sentiment_score == 0:
        positive_percentage = 10.0
        negative_percentage = 10.0
        neutral_percentage = 80.0

    else:
        difference = positive_score - negative_score

        if difference > 0:
            confidence = min(abs(difference) / total_sentiment_score, 1.0)

            positive_percentage = 50.0 + (confidence * 45.0)
            negative_percentage = 5.0 + ((1.0 - confidence) * 20.0)
            neutral_percentage = 100.0 - positive_percentage - negative_percentage

        elif difference < 0:
            confidence = min(abs(difference) / total_sentiment_score, 1.0)

            negative_percentage = 50.0 + (confidence * 45.0)
            positive_percentage = 5.0 + ((1.0 - confidence) * 20.0)
            neutral_percentage = 100.0 - negative_percentage - positive_percentage

        else:
            positive_percentage = 15.0
            negative_percentage = 15.0
            neutral_percentage = 70.0

    positive_percentage = max(0.0, min(100.0, positive_percentage))
    negative_percentage = max(0.0, min(100.0, negative_percentage))
    neutral_percentage = max(
        0.0,
        min(100.0, 100.0 - positive_percentage - negative_percentage)
    )

    total_emotions = sum(emotion_scores.values())

    if total_emotions == 0:

        if positive_percentage > negative_percentage:
            emotion_det = EmotionDetection(
                happy=45.0,
                angry=5.0,
                excited=20.0,
                frustrated=5.0,
                satisfied=25.0
            )

        elif negative_percentage > positive_percentage:
            emotion_det = EmotionDetection(
                happy=5.0,
                angry=30.0,
                excited=5.0,
                frustrated=45.0,
                satisfied=15.0
            )

        else:
            emotion_det = EmotionDetection(
                happy=20.0,
                angry=10.0,
                excited=15.0,
                frustrated=15.0,
                satisfied=40.0
            )

    else:

        emotion_det = EmotionDetection(
            happy=round(
                emotion_scores["happy"] / total_emotions * 100,
                1
            ),
            angry=round(
                emotion_scores["angry"] / total_emotions * 100,
                1
            ),
            excited=round(
                emotion_scores["excited"] / total_emotions * 100,
                1
            ),
            frustrated=round(
                emotion_scores["frustrated"] / total_emotions * 100,
                1
            ),
            satisfied=round(
                emotion_scores["satisfied"] / total_emotions * 100,
                1
            )
        )

    common_keywords = [
        item[0]
        for item in Counter(keyword_words).most_common(8)
    ]

    if not common_keywords:
        common_keywords = [
            "service",
            "product",
            "experience"
        ]

    total = positive_percentage + negative_percentage + neutral_percentage

    if total != 100:
        neutral_percentage = round(
            100.0 - positive_percentage - negative_percentage,
            1
        )

    return SentimentResponse(
        positive_percentage=round(positive_percentage, 1),
        negative_percentage=round(negative_percentage, 1),
        neutral_percentage=round(neutral_percentage, 1),
        keywords=common_keywords,
        emotions=emotion_det
    )


@router.post("/analyze", response_model=SentimentResponse)
async def analyze_reviews(
    req: SentimentRequest,
    current_user: User = Depends(get_current_user)
):

    if not req.reviews or not req.reviews.strip():
        raise HTTPException(
            status_code=400,
            detail="Reviews text cannot be empty."
        )

    return analyze_lexicon_sentiment(req.reviews)