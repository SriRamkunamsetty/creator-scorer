"""Semantic NLP comment analysis and bot network detection."""
from collections import Counter
import math
import re
from typing import Dict, List, Optional, Tuple, Any


class NLPBotDetector:
    """Detects bot activity, astroturfing, and comment farming using NLP metrics:

    - Lexical Shannon Entropy (information density per token)
    - Type-Token Ratio (TTR) and Hapax Legomena frequency
    - N-gram TF-IDF semantic redundancy and duplicate clustering
    - Emoji and zero-lexicon spam density
    """

    def __init__(self, min_sample_size: int = 5):
        self.min_sample_size = min_sample_size

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return [w for w in cleaned.split() if len(w) > 1]

    @staticmethod
    def _shannon_entropy(tokens: List[str]) -> float:
        if not tokens:
            return 0.0
        n = len(tokens)
        counts = Counter(tokens)
        return -sum((c / n) * math.log2(c / n) for c in counts.values())

    @staticmethod
    def _ngram_char_tfidf(texts: List[str], n: int = 3) -> List[Dict[str, float]]:
        """Character n-gram TF-IDF representations without external C-extensions."""
        doc_ngrams = []
        df: Counter = Counter()
        for t in texts:
            norm = re.sub(r"\s+", " ", t.lower().strip())
            ng = [norm[i : i + n] for i in range(max(0, len(norm) - n + 1))] if len(norm) >= n else [norm]
            counts = Counter(ng)
            doc_ngrams.append(counts)
            for k in counts.keys():
                df[k] += 1

        n_docs = max(1, len(texts))
        vectors = []
        for counts in doc_ngrams:
            total = sum(counts.values()) or 1
            vec: Dict[str, float] = {}
            for term, c in counts.items():
                tf = c / total
                idf = math.log((1 + n_docs) / (1 + df[term])) + 1.0
                vec[term] = tf * idf
            # L2 normalize
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            vectors.append({k: v / norm for k, v in vec.items()})
        return vectors

    @staticmethod
    def _cosine_sim(v1: Dict[str, float], v2: Dict[str, float]) -> float:
        if len(v1) > len(v2):
            v1, v2 = v2, v1
        dot = sum(v * v2.get(k, 0.0) for k, v in v1.items())
        return max(0.0, min(1.0, dot))

    def analyze_comments(self, comments: List[str]) -> Dict[str, Any]:
        """Analyze a collection of comments and return a comprehensive bot score and signals."""
        filtered = [c.strip() for c in comments if c and c.strip()]
        if len(filtered) < self.min_sample_size:
            return {
                "evaluable": False,
                "bot_probability": None,
                "confidence": "insufficient_data",
                "details": f"Sample size ({len(filtered)}) below minimum threshold ({self.min_sample_size})",
                "signals": [],
            }

        total_comments = len(filtered)
        all_tokens = []
        doc_tokens = []
        emoji_only_count = 0

        for c in filtered:
            toks = self._tokenize(c)
            doc_tokens.append(toks)
            all_tokens.extend(toks)
            if not toks:
                emoji_only_count += 1

        # 1. Lexical Diversity & Entropy
        total_tokens = len(all_tokens)
        unique_tokens = len(set(all_tokens))
        ttr = unique_tokens / total_tokens if total_tokens > 0 else 0.0
        entropy = self._shannon_entropy(all_tokens)

        # 2. Semantic Clustering via TF-IDF Cosine Similarity
        vectors = self._ngram_char_tfidf(filtered, n=3)
        high_sim_pairs = 0
        total_pairs = 0
        sum_sim = 0.0

        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                sim = self._cosine_sim(vectors[i], vectors[j])
                sum_sim += sim
                total_pairs += 1
                if sim >= 0.70:
                    high_sim_pairs += 1

        mean_sim = sum_sim / total_pairs if total_pairs > 0 else 0.0
        dense_cluster_ratio = high_sim_pairs / total_pairs if total_pairs > 0 else 0.0
        emoji_ratio = emoji_only_count / total_comments

        # 3. Signals & Explanations
        signals = []
        score_components = []

        # Signal A: Semantic Redundancy
        if dense_cluster_ratio >= 0.25:
            signals.append({
                "name": "semantic_redundancy",
                "severity": "high" if dense_cluster_ratio >= 0.45 else "medium",
                "description": f"{dense_cluster_ratio:.1%} of comment pairs share near-identical phrasing (bot pattern)",
            })
            score_components.append(min(1.0, dense_cluster_ratio * 1.8))
        else:
            score_components.append(0.0)

        # Signal B: Vocabulary Entropy Deficit
        # Natural English comments typically have entropy > 4.5 for samples > 20 tokens
        if total_tokens >= 15 and entropy < 3.2:
            signals.append({
                "name": "low_lexical_entropy",
                "severity": "high" if entropy < 2.5 else "medium",
                "description": f"Abnormally low Shannon entropy ({entropy:.2f} bits/token, natural discourse > 3.8)",
            })
            score_components.append(max(0.0, (3.5 - entropy) / 2.0))
        else:
            score_components.append(0.0)

        # Signal C: Low Type-Token Ratio
        if total_tokens >= 20 and ttr < 0.40:
            signals.append({
                "name": "vocabulary_constriction",
                "severity": "medium",
                "description": f"Repetitive keyword recycling (Type-Token Ratio {ttr:.1%})",
            })
            score_components.append(max(0.0, (0.50 - ttr) * 1.5))
        else:
            score_components.append(0.0)

        # Signal D: Non-lexical / Emoji Spam
        if emoji_ratio >= 0.30:
            signals.append({
                "name": "emoji_spam_density",
                "severity": "high" if emoji_ratio >= 0.50 else "medium",
                "description": f"{emoji_ratio:.1%} of comments contain zero substantive words",
            })
            score_components.append(min(1.0, emoji_ratio * 1.4))
        else:
            score_components.append(0.0)

        # Weighted combination for overall bot probability
        weights = [0.40, 0.25, 0.15, 0.20]
        bot_prob = sum(w * s for w, s in zip(weights, score_components))
        bot_prob = round(max(0.0, min(1.0, bot_prob)), 3)

        return {
            "evaluable": True,
            "bot_probability": bot_prob,
            "confidence": "high" if total_comments >= 12 else "medium",
            "metrics": {
                "total_comments_sampled": total_comments,
                "shannon_entropy": round(entropy, 2),
                "type_token_ratio": round(ttr, 3),
                "mean_pairwise_similarity": round(mean_sim, 3),
                "dense_cluster_ratio": round(dense_cluster_ratio, 3),
                "emoji_only_ratio": round(emoji_ratio, 3),
            },
            "signals": signals,
        }
