package ai

import (
	"regexp"
	"strings"
)

// stopWords are common English words filtered out of search queries.
var stopWords = map[string]bool{
	"the": true, "a": true, "an": true, "and": true, "or": true, "but": true,
	"in": true, "on": true, "at": true, "to": true, "for": true, "of": true,
	"by": true, "with": true, "from": true, "that": true, "this": true, "these": true,
	"those": true, "is": true, "are": true, "was": true, "were": true, "be": true,
	"been": true, "being": true, "have": true, "has": true, "had": true, "do": true,
	"does": true, "did": true, "will": true, "would": true, "shall": true, "should": true,
	"may": true, "might": true, "can": true, "could": true, "not": true, "no": true,
	"nor": true, "all": true, "each": true, "every": true, "both": true, "few": true,
	"more": true, "most": true, "other": true, "some": true, "such": true, "than": true,
	"also": true, "very": true, "just": true, "about": true, "above": true, "after": true,
	"again": true, "against": true, "below": true, "between": true, "into": true,
	"through": true, 	"during": true, "before": true, "up": true, "down": true,
	"out": true, "off": true, "over": true, "under": true, "then": true, "once": true,
	"here": true, "there": true, "when": true, "where": true, "why": true, "how": true,
	"he": true, "she": true, "it": true, "they": true, "we": true, "you": true,
	"me": true, "him": true, "her": true, "us": true, "them": true, "my": true,
	"thy": true, "his": true, "its": true, "our": true, "your": true, "their": true,
	"who": true, "whom": true, "which": true, "what": true, "unto": true, "upon": true,
	"doth": true, "hath": true, "art": true, "thou": true, "thee": true,
}

// nonAlpha matches anything that isn't a letter.
var nonAlpha = regexp.MustCompile(`[^a-zA-Z]+`)

// BuildSearchQuery extracts meaningful keywords from verse text for image search.
//
// Strategy:
//  1. Strip punctuation and digits
//  2. Remove stop words
//  3. Extract top 3-5 words by length (longer words are more specific)
//  4. Add "bible" qualifier
//
// Examples:
//
//	"I am the good shepherd: the good shepherd giveth his life for the sheep."
//	→ "good shepherd bible"
//
//	"In the beginning God created the heaven and the earth."
//	→ "beginning god created heaven earth bible"
func BuildSearchQuery(verseText, reference string) string {
	// Normalize
	text := strings.ToLower(verseText)
	text = strings.ReplaceAll(text, ":", " ")
	text = strings.ReplaceAll(text, ";", " ")
	text = strings.ReplaceAll(text, ",", " ")
	text = strings.ReplaceAll(text, ".", " ")
	text = strings.ReplaceAll(text, "\"", " ")
	text = strings.ReplaceAll(text, "'", " ")
	text = strings.ReplaceAll(text, "!", " ")
	text = strings.ReplaceAll(text, "?", " ")

	// Split into words
	rawWords := strings.Fields(text)

	// Filter stop words and short words, collect meaningful ones
	var candidates []string
	seen := make(map[string]bool)
	for _, w := range rawWords {
		w = strings.TrimSpace(w)
		if len(w) < 3 || stopWords[w] || seen[w] {
			continue
		}
		seen[w] = true
		candidates = append(candidates, w)
	}

	// Sort by length descending (longer words = more specific)
	// Simple insertion sort for small lists
	for i := 1; i < len(candidates); i++ {
		for j := i; j > 0 && len(candidates[j]) > len(candidates[j-1]); j-- {
			candidates[j], candidates[j-1] = candidates[j-1], candidates[j]
		}
	}

	// Take top 4
	maxWords := 4
	if len(candidates) < maxWords {
		maxWords = len(candidates)
	}
	keywords := candidates[:maxWords]

	// Build query
	query := strings.Join(keywords, " ")
	if query == "" {
		// Fallback: use book name from reference
		if ref := strings.Split(reference, "."); len(ref) > 0 {
			query = ref[0] + " bible"
		} else {
			query = "bible verse"
		}
	} else {
		query += " bible"
	}

	return query
}
