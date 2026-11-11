// Mock lecture used until the backend is ready.
// Concepts come from C's real concept graph for CSCI 3151 M04 (linear regression),
// trimmed to 10 concepts so the mastery map stays readable in the demo.
// Questions, explanations and quotes are hand-written placeholders.

import type { Concept, QuestionType } from "../types";

export const MOCK_LECTURE_TITLE = "CSCI 3151 · M04 Linear Regression";
export const MOCK_PAGE_COUNT = 32;

export const MOCK_CONCEPTS: Concept[] = [
  {
    id: "loss_function_and_metric",
    name: "Loss function vs evaluation metric",
    summary: "A loss scores a single prediction and is minimized in training; a metric summarizes performance to judge whether a model is good enough.",
    pages: [4],
    prerequisites: [],
  },
  {
    id: "expected_risk",
    name: "Expected risk",
    summary: "The average loss of a model over the unknown data-generating distribution, which we can never compute directly.",
    pages: [5, 7],
    prerequisites: ["loss_function_and_metric"],
  },
  {
    id: "empirical_risk",
    name: "Empirical risk",
    summary: "The average loss over the training set, used as a practical stand-in for expected risk and minimized to choose a model.",
    pages: [6, 7],
    prerequisites: ["expected_risk"],
  },
  {
    id: "squared_vs_absolute_loss",
    name: "Squared (L2) vs absolute (L1) loss",
    summary: "Squared loss penalizes large errors quadratically and reacts more strongly to outliers than absolute loss, which penalizes them linearly.",
    pages: [8],
    prerequisites: ["loss_function_and_metric"],
  },
  {
    id: "linear_regression_1d",
    name: "1D linear regression and residuals",
    summary: "Model a scalar target with a line w1*x + w0; the residual is the gap between prediction and target.",
    pages: [9, 13, 14],
    prerequisites: [],
  },
  {
    id: "regression_cost_function",
    name: "Squared-loss cost J(w1, w0)",
    summary: "Training 1D linear regression means finding the weights that minimize the average squared residual J(w1, w0).",
    pages: [10],
    prerequisites: ["linear_regression_1d", "empirical_risk", "squared_vs_absolute_loss"],
  },
  {
    id: "cost_surface_convexity",
    name: "Cost surface and convexity",
    summary: "Viewed over the weights, the squared-loss cost is a convex quadratic bowl, so any local minimum is a global minimum.",
    pages: [11, 12, 15, 16],
    prerequisites: ["regression_cost_function"],
  },
  {
    id: "gradient_descent",
    name: "Gradient descent",
    summary: "Repeatedly move the weights against the gradient of the cost, scaled by a learning rate, until reaching the minimum.",
    pages: [17, 19],
    prerequisites: ["cost_surface_convexity"],
  },
  {
    id: "multivariate_regression",
    name: "Multivariate regression (bias trick)",
    summary: "Stack inputs into a matrix and append a column of ones so all predictions and the cost are written as matrix expressions.",
    pages: [20],
    prerequisites: ["regression_cost_function"],
  },
  {
    id: "normal_equation",
    name: "Normal equation",
    summary: "Setting the gradient of the cost to zero gives w* = (XᵀX)⁻¹Xᵀt when XᵀX is invertible; fast for moderate dimensions.",
    pages: [21, 22],
    prerequisites: ["multivariate_regression", "cost_surface_convexity"],
  },
];

export interface BankItem {
  type: QuestionType;
  prompt: string;
  options?: string[];
  answer?: string; // correct option letter for multiple_choice
  keywords?: string[][]; // short_answer: every group must have at least one match
}

// Two questions per concept: the first is used for coverage, the second for re-tests.
export const QUESTION_BANK: Record<string, BankItem[]> = {
  loss_function_and_metric: [
    {
      type: "multiple_choice",
      prompt: "What is the main difference between a loss function and an evaluation metric?",
      options: [
        "A. A loss is used only at test time; a metric only during training.",
        "B. A loss scores individual predictions and is minimized in training; a metric summarizes how good the model is.",
        "C. They are always the same function.",
        "D. A metric must be differentiable; a loss does not need to be.",
      ],
      answer: "B",
    },
    {
      type: "multiple_choice",
      prompt: "Accuracy is often reported for classifiers. Why is it usually NOT minimized directly during training?",
      options: [
        "A. Accuracy is a loss, not a metric.",
        "B. It is not differentiable with respect to the weights, so it is a poor training objective.",
        "C. It is always larger than the loss.",
        "D. It can only be computed on the test set.",
      ],
      answer: "B",
    },
  ],
  expected_risk: [
    {
      type: "multiple_choice",
      prompt: "What is the expected risk of a model?",
      options: [
        "A. Its average loss on the training set.",
        "B. Its average loss over the true, unknown data distribution.",
        "C. The largest loss on any single example.",
        "D. Its loss on the validation set.",
      ],
      answer: "B",
    },
    {
      type: "multiple_choice",
      prompt: "Why can't we compute the expected risk directly?",
      options: [
        "A. The loss function is not differentiable.",
        "B. The data-generating distribution is unknown.",
        "C. It needs infinitely many training epochs.",
        "D. It is only defined for classification.",
      ],
      answer: "B",
    },
  ],
  empirical_risk: [
    {
      type: "multiple_choice",
      prompt: "Which statement best describes empirical risk?",
      options: [
        "A. The average loss over the training set, used as a stand-in for expected risk.",
        "B. The loss on one held-out example.",
        "C. Expected risk multiplied by the number of samples.",
        "D. The variance of the loss across examples.",
      ],
      answer: "A",
    },
    {
      type: "multiple_choice",
      prompt: "Empirical risk minimization chooses the model that…",
      options: [
        "A. has the best validation metric.",
        "B. has the lowest average loss on the training data.",
        "C. maximizes the likelihood of the test set.",
        "D. has the fewest parameters.",
      ],
      answer: "B",
    },
  ],
  squared_vs_absolute_loss: [
    {
      type: "multiple_choice",
      prompt: "Compared with absolute (L1) loss, squared (L2) loss…",
      options: [
        "A. penalizes large errors more and is more sensitive to outliers.",
        "B. ignores outliers completely.",
        "C. penalizes every error by the same amount.",
        "D. cannot be used for regression.",
      ],
      answer: "A",
    },
    {
      type: "multiple_choice",
      prompt: "A residual of 4 contributes how much to the squared loss and to the absolute loss?",
      options: ["A. 4 and 16", "B. 16 and 4", "C. 8 and 4", "D. 16 and 2"],
      answer: "B",
    },
  ],
  linear_regression_1d: [
    {
      type: "multiple_choice",
      prompt: "In 1D linear regression y = w1·x + w0, what is the residual for one data point?",
      options: [
        "A. The slope w1.",
        "B. The gap between the prediction and the true target.",
        "C. The squared input x².",
        "D. The intercept w0.",
      ],
      answer: "B",
    },
    {
      type: "multiple_choice",
      prompt: "If w1 = 2 and w0 = 1, what does the model predict for x = 3?",
      options: ["A. 5", "B. 6", "C. 7", "D. 9"],
      answer: "C",
    },
  ],
  regression_cost_function: [
    {
      type: "multiple_choice",
      prompt: "Training 1D linear regression with squared loss means…",
      options: [
        "A. choosing w1, w0 that minimize the average squared residual J(w1, w0).",
        "B. choosing the single data point with the smallest residual.",
        "C. maximizing J(w1, w0).",
        "D. always setting w0 = 0.",
      ],
      answer: "A",
    },
    {
      type: "short_answer",
      prompt: "In one sentence: what does the cost J(w1, w0) measure for linear regression?",
      keywords: [
        ["average", "mean"],
        ["squar", "residual", "error"],
      ],
    },
  ],
  cost_surface_convexity: [
    {
      type: "multiple_choice",
      prompt: "For linear regression with squared loss, the cost viewed as a function of the weights is…",
      options: [
        "A. a convex bowl, so any local minimum is the global minimum.",
        "B. full of local minima.",
        "C. a straight line.",
        "D. always zero at w = 0.",
      ],
      answer: "A",
    },
    {
      type: "multiple_choice",
      prompt: "Why does convexity of the cost matter for training?",
      options: [
        "A. It makes the model nonlinear.",
        "B. Gradient descent cannot get stuck in a bad local minimum.",
        "C. It removes the need for a learning rate.",
        "D. It guarantees zero training error.",
      ],
      answer: "B",
    },
  ],
  gradient_descent: [
    {
      type: "multiple_choice",
      prompt: "Which is the gradient descent update rule (α is the learning rate)?",
      options: ["A. w ← w + α∇J(w)", "B. w ← w − α∇J(w)", "C. w ← ∇J(w)", "D. w ← w / α"],
      answer: "B",
    },
    {
      type: "multiple_choice",
      prompt: "What can happen if the learning rate α is far too large?",
      options: [
        "A. Training always converges faster with no downside.",
        "B. The updates overshoot and the cost can diverge.",
        "C. The gradient becomes exactly zero.",
        "D. The model becomes nonlinear.",
      ],
      answer: "B",
    },
  ],
  multivariate_regression: [
    {
      type: "multiple_choice",
      prompt: "What is the 'bias trick' in multivariate linear regression?",
      options: [
        "A. Removing the intercept from the model.",
        "B. Appending a column of ones to X so w0 becomes part of the weight vector.",
        "C. Adding random noise to the inputs.",
        "D. Normalizing the targets to mean zero.",
      ],
      answer: "B",
    },
    {
      type: "multiple_choice",
      prompt: "With design matrix X (one row per example, bias column included) and weights w, the predictions for all examples are…",
      options: ["A. wᵀX", "B. Xw", "C. X + w", "D. XᵀX"],
      answer: "B",
    },
  ],
  normal_equation: [
    {
      type: "multiple_choice",
      prompt: "The normal equation gives the least-squares weights as…",
      options: ["A. w* = (XᵀX)⁻¹Xᵀt", "B. w* = Xᵀt", "C. w* = (XXᵀ)t", "D. w* = X⁻¹"],
      answer: "A",
    },
    {
      type: "multiple_choice",
      prompt: "When is the normal equation a poor choice compared with gradient descent?",
      options: [
        "A. When the dataset is small.",
        "B. When there are very many features, because inverting XᵀX becomes expensive.",
        "C. When the cost is convex.",
        "D. Never; it is always better.",
      ],
      answer: "B",
    },
  ],
};

// Re-explanation shown when a concept is identified as the root cause.
export const EXPLANATIONS: Record<string, { text: string; page: number; quote: string }> = {
  loss_function_and_metric: {
    text: "A loss function scores one prediction (for example, squared error) and is what training minimizes. An evaluation metric (for example, accuracy or RMSE) summarizes overall performance so you can judge whether the model is good enough. They can differ: accuracy is a useful metric but a poor loss because it is not differentiable.",
    page: 4,
    quote: "Loss: score for one prediction, minimized during training.",
  },
  expected_risk: {
    text: "Expected risk is the average loss the model would incur over the true data-generating distribution. Because that distribution is unknown, we can never compute it exactly; we can only estimate it from data.",
    page: 5,
    quote: "Expected risk averages the loss over the data distribution.",
  },
  empirical_risk: {
    text: "Empirical risk replaces the unknown distribution with the training set: it is the average loss over the N training examples. Empirical risk minimization picks the model with the lowest training loss as a practical stand-in for minimizing expected risk.",
    page: 6,
    quote: "Empirical risk: average loss over the training set.",
  },
  squared_vs_absolute_loss: {
    text: "Squared loss squares each residual, so an error of 4 costs 16 while absolute loss charges 4. That makes squared loss react much more strongly to large errors and outliers.",
    page: 8,
    quote: "L2 penalizes large residuals quadratically.",
  },
  linear_regression_1d: {
    text: "1D linear regression predicts y = w1·x + w0, where w1 is the slope and w0 the intercept. The residual for one example is the gap between the prediction and the true target.",
    page: 9,
    quote: "Residual = prediction − target.",
  },
  regression_cost_function: {
    text: "The cost J(w1, w0) is the average squared residual over the training set. Training means searching for the weights that make J as small as possible: it is empirical risk with squared loss.",
    page: 10,
    quote: "J(w1, w0): mean of squared residuals.",
  },
  cost_surface_convexity: {
    text: "Plotted over the weights, the squared-loss cost forms a convex bowl. A convex function has no bad local minima: any minimum you reach is the global one, which is why gradient descent works reliably here.",
    page: 11,
    quote: "The cost surface is a convex quadratic bowl.",
  },
  gradient_descent: {
    text: "Gradient descent repeatedly moves the weights a small step against the gradient: w ← w − α∇J(w). The learning rate α sets the step size; too large and the updates overshoot, too small and training is slow.",
    page: 17,
    quote: "Step against the gradient, scaled by α.",
  },
  multivariate_regression: {
    text: "With several inputs, stack the examples into a matrix X and append a column of ones (the bias trick) so the intercept becomes just another weight. Then all predictions are the single matrix product Xw.",
    page: 20,
    quote: "Append a column of ones to absorb the bias.",
  },
  normal_equation: {
    text: "Setting the gradient of the cost to zero gives the closed-form solution w* = (XᵀX)⁻¹Xᵀt. It needs no learning rate, but inverting XᵀX gets expensive when there are many features.",
    page: 21,
    quote: "w* = (XᵀX)⁻¹Xᵀt",
  },
};
