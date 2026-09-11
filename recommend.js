/*
  Moodshop recommendation engine.

  Pure, deterministic, and completely separate from the UI: no DOM, no
  fetch, no randomness, no model. The same answers always produce the same
  result, which is the point — a tool that tells you something different
  every time you answer it the same way is not telling you anything.

  Scoring is plain weighted addition over content/feelings.json. Ties break
  on a fixed published order rather than object key order, so the result
  can't drift when the data file is re-serialised.

  Everything here is attached to window.MoodshopRecommend and is safe to
  call before any tool renders.
*/

/**
 * @typedef {Object} FeelingTheme
 * @property {string} card      CSS background for a mood card
 * @property {string} cardInk   Foreground colour that clears AA on `card`
 * @property {string} accent    Page accent when this feeling is in focus
 *
 * @typedef {Object} Feeling
 * @property {string}   slug
 * @property {string}   name
 * @property {string}   emoji
 * @property {string}   shortDescription
 * @property {string}   whyFits
 * @property {string[]} related            Other feeling slugs
 * @property {string}   product            Purchasable mood slug this resolves to
 * @property {?string}  productNote        Set when `product` is a different feeling
 * @property {FeelingTheme} theme
 *
 * @typedef {Object} QuizOption
 * @property {string} label
 * @property {string} echo                 Restatement used to explain the result
 * @property {Object<string, number>} weights
 *
 * @typedef {Object} QuizQuestion
 * @property {string} id
 * @property {string} prompt
 * @property {QuizOption[]} options
 *
 * @typedef {Object} Recommendation
 * @property {Feeling}   primaryMood
 * @property {Feeling[]} secondaryMoods
 * @property {string}    explanation
 * @property {Object<string, number>} scores
 */

(function (global) {
  "use strict";

  var DATA = global.MOODSHOP_FEELINGS || { feelings: [], quiz: { questions: [], tiebreak: [] } };
  var FEELINGS = DATA.feelings || [];
  var QUIZ = DATA.quiz || { questions: [], tiebreak: [] };

  /** @type {Object<string, Feeling>} */
  var BY_SLUG = {};
  FEELINGS.forEach(function (f) { BY_SLUG[f.slug] = f; });

  /**
   * @param {string} slug
   * @returns {?Feeling}
   */
  function feeling(slug) {
    return Object.prototype.hasOwnProperty.call(BY_SLUG, slug) ? BY_SLUG[slug] : null;
  }

  /**
   * Where a feeling actually sends someone to buy. Several feelings have no
   * piece of their own yet and resolve onto the nearest one that exists;
   * `note` is the sentence that says so out loud rather than quietly
   * swapping the product under the reader.
   *
   * @param {string|Feeling} slugOrFeeling
   * @returns {?{mood: string, note: ?string, href: string}}
   */
  function resolveProduct(slugOrFeeling) {
    var f = typeof slugOrFeeling === "string" ? feeling(slugOrFeeling) : slugOrFeeling;
    if (!f || !f.product) return null;
    return { mood: f.product, note: f.productNote || null, href: "/mood/" + f.product + "/" };
  }

  /**
   * Weighted scoring over the answered questions.
   *
   * @param {Object<string, number>} answers  question id -> chosen option index
   * @returns {?Recommendation} null when nothing was answered
   */
  function getMoodRecommendation(answers) {
    var scores = {};
    var echoes = [];
    var answered = 0;

    FEELINGS.forEach(function (f) { scores[f.slug] = 0; });

    QUIZ.questions.forEach(function (q) {
      var idx = answers ? answers[q.id] : undefined;
      if (idx === undefined || idx === null) return;
      var opt = q.options[idx];
      if (!opt) return;
      answered++;
      echoes.push(opt.echo);
      Object.keys(opt.weights).forEach(function (slug) {
        if (scores[slug] === undefined) return;   // unknown slug in data: ignore, don't crash
        scores[slug] += opt.weights[slug];
      });
    });

    if (!answered) return null;

    // Highest score wins; equal scores break on the published order, never on
    // whatever order the keys happen to come back in.
    var order = QUIZ.tiebreak && QUIZ.tiebreak.length
      ? QUIZ.tiebreak
      : FEELINGS.map(function (f) { return f.slug; });

    var ranked = order.slice().filter(function (s) { return scores[s] !== undefined; });
    ranked.sort(function (a, b) {
      if (scores[b] !== scores[a]) return scores[b] - scores[a];
      return order.indexOf(a) - order.indexOf(b);
    });

    var primary = feeling(ranked[0]);
    if (!primary) return null;

    // Seconds: the next highest that actually scored, topped up from the
    // primary's own related list so there are always three to offer.
    var secondary = [];
    ranked.slice(1).forEach(function (s) {
      if (secondary.length < 3 && scores[s] > 0) secondary.push(feeling(s));
    });
    (primary.related || []).forEach(function (s) {
      if (secondary.length < 3 && s !== primary.slug &&
          secondary.indexOf(feeling(s)) === -1 && feeling(s)) {
        secondary.push(feeling(s));
      }
    });

    return {
      primaryMood: primary,
      secondaryMoods: secondary,
      explanation: explain(echoes, primary),
      scores: scores
    };
  }

  /**
   * @param {string[]} echoes
   * @param {Feeling} primary
   * @returns {string}
   */
  function explain(echoes, primary) {
    var said;
    if (echoes.length === 1) said = echoes[0];
    else if (echoes.length === 2) said = echoes[0] + " and " + echoes[1];
    else said = echoes.slice(0, -1).join(", ") + " and " + echoes[echoes.length - 1];
    return "You said " + said + ". " + primary.whyFits;
  }

  /**
   * One feeling a day, the same one for everybody, changing at UTC midnight.
   * Indexed off the epoch day rather than the day of the year so it doesn't
   * repeat or jump across a year boundary.
   *
   * @param {Array<{slug: string}>} pool
   * @param {Date} [now]
   * @returns {?Object}
   */
  function ofTheDay(pool, now) {
    if (!pool || !pool.length) return null;
    var d = now || new Date();
    var day = Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86400000);
    return pool[((day % pool.length) + pool.length) % pool.length];
  }

  /**
   * Deterministic pick from a list, varied by a counter rather than
   * Math.random so "another one" walks the whole list before repeating.
   *
   * @param {Array} list
   * @param {number} n
   * @returns {*}
   */
  function cycle(list, n) {
    if (!list || !list.length) return null;
    return list[((n % list.length) + list.length) % list.length];
  }

  global.MoodshopRecommend = {
    feelings: FEELINGS,
    quiz: QUIZ,
    feeling: feeling,
    resolveProduct: resolveProduct,
    getMoodRecommendation: getMoodRecommendation,
    ofTheDay: ofTheDay,
    cycle: cycle
  };
})(typeof window !== "undefined" ? window : this);
