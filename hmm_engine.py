"""
Pure-Python 2-State Gaussian Hidden Markov Model (HMM) for Financial Regimes
=============================================================================
Designed for clarity, intuitive understanding, and zero third-party C dependencies.

Concepts:
- State 0: Low-Volatility / Bull Regime (Steady positive returns, calm market)
- State 1: High-Volatility / Correction Regime (Large swings, negative skew, panic)
"""

import math
import csv

class SimpleGaussianHMM2State:
    def __init__(self):
        # Initial parameters (will be learned from the data)
        # mu: average daily return for [State 0, State 1]
        self.mu = [0.08, -0.15]
        
        # sigma: daily volatility (standard deviation) for [State 0, State 1]
        self.sigma = [0.65, 1.80]
        
        # Transition matrix A[i][j] = probability of moving from State i to State j
        # Markets are "sticky": if calm today, likely calm tomorrow (e.g. 95% chance)
        self.A = [
            [0.96, 0.04],  # From Calm -> [Stay Calm (96%), Turn Panic (4%)]
            [0.10, 0.90]   # From Panic -> [Turn Calm (10%), Stay Panic (90%)]
        ]
        
        # Prior probability of starting in State 0 vs State 1
        self.pi = [0.80, 0.20]

    def gaussian_pdf(self, x, state):
        """
        Computes the standard normal bell-curve probability density:
        f(x) = (1 / (sigma * sqrt(2*pi))) * exp( - (x - mu)^2 / (2 * sigma^2) )
        """
        mu = self.mu[state]
        sig = max(self.sigma[state], 1e-4)
        diff = x - mu
        exponent = - (diff * diff) / (2.0 * sig * sig)
        # Protect against extreme underflow
        if exponent < -500:
            return 1e-100
        return (1.0 / (sig * math.sqrt(2.0 * math.pi))) * math.exp(exponent)

    def fit(self, observations, max_iter=40, tol=1e-4):
        """
        Baum-Welch (Expectation-Maximization) Algorithm in plain English:
        1. E-Step: Calculate how likely each day belongs to State 0 vs State 1
        2. M-Step: Update the average return (mu) and volatility (sigma) for each state
        Repeat until parameters stop changing.
        """
        T = len(observations)
        print(f"Training 2-State HMM on {T} observations...")
        
        # Smart initialization based on data
        mean_all = sum(observations) / T
        variance_all = sum((x - mean_all)**2 for x in observations) / T
        std_all = math.sqrt(variance_all)
        
        # State 0 (Calm): higher return, lower vol
        # State 1 (Turbulent): lower return, higher vol
        self.mu = [mean_all + 0.05, mean_all - 0.15]
        self.sigma = [std_all * 0.70, std_all * 1.80]

        for iteration in range(max_iter):
            # ----------------------------------------------------
            # 1. FORWARD PASS: alpha[t][state] = P(obs_1..t and state at t)
            # ----------------------------------------------------
            alpha = []
            c = []  # scaling factors to prevent numeric underflow
            
            # t = 0
            alpha_0 = [self.pi[i] * self.gaussian_pdf(observations[0], i) for i in range(2)]
            c_0 = sum(alpha_0) or 1e-12
            alpha.append([a / c_0 for a in alpha_0])
            c.append(c_0)
            
            # t = 1 .. T-1
            for t in range(1, T):
                alpha_t = []
                for j in range(2):
                    prob_from_prev = alpha[t-1][0] * self.A[0][j] + alpha[t-1][1] * self.A[1][j]
                    emit = self.gaussian_pdf(observations[t], j)
                    alpha_t.append(prob_from_prev * emit)
                c_t = sum(alpha_t) or 1e-12
                alpha.append([a / c_t for a in alpha_t])
                c.append(c_t)

            # ----------------------------------------------------
            # 2. BACKWARD PASS: beta[t][state]
            # ----------------------------------------------------
            beta = [[0.0, 0.0] for _ in range(T)]
            beta[T-1] = [1.0, 1.0]
            
            for t in range(T-2, -1, -1):
                for i in range(2):
                    beta[t][i] = (
                        self.A[i][0] * self.gaussian_pdf(observations[t+1], 0) * beta[t+1][0] +
                        self.A[i][1] * self.gaussian_pdf(observations[t+1], 1) * beta[t+1][1]
                    ) / c[t+1]

            # ----------------------------------------------------
            # 3. POSTERIOR PROBABILITIES (Gamma & Xi)
            # gamma[t][i] = probability of being in State i at time t
            # ----------------------------------------------------
            gamma = []
            for t in range(T):
                denom = alpha[t][0] * beta[t][0] + alpha[t][1] * beta[t][1] or 1e-12
                g0 = (alpha[t][0] * beta[t][0]) / denom
                g1 = (alpha[t][1] * beta[t][1]) / denom
                gamma.append([g0, g1])

            # xi[t][i][j] = prob of transitioning from state i at t to state j at t+1
            xi_sum = [[0.0, 0.0], [0.0, 0.0]]
            for t in range(T-1):
                denom = sum(
                    alpha[t][i] * self.A[i][j] * self.gaussian_pdf(observations[t+1], j) * beta[t+1][j]
                    for i in range(2) for j in range(2)
                ) or 1e-12
                for i in range(2):
                    for j in range(2):
                        xi_val = (alpha[t][i] * self.A[i][j] * self.gaussian_pdf(observations[t+1], j) * beta[t+1][j]) / denom
                        xi_sum[i][j] += xi_val

            # ----------------------------------------------------
            # 4. M-STEP: UPDATE PARAMETERS
            # ----------------------------------------------------
            old_mu = list(self.mu)
            
            # Initial state prob
            self.pi = [gamma[0][0], gamma[0][1]]
            
            # Update Transition Matrix A
            for i in range(2):
                gamma_sum_i = sum(gamma[t][i] for t in range(T-1)) or 1e-12
                self.A[i][0] = xi_sum[i][0] / gamma_sum_i
                self.A[i][1] = xi_sum[i][1] / gamma_sum_i
                # Normalize row to sum to 1.0
                row_sum = self.A[i][0] + self.A[i][1]
                self.A[i][0] /= row_sum
                self.A[i][1] /= row_sum

            # Update Means and Standard Deviations
            for i in range(2):
                gamma_sum = sum(gamma[t][i] for t in range(T)) or 1e-12
                self.mu[i] = sum(gamma[t][i] * observations[t] for t in range(T)) / gamma_sum
                var_i = sum(gamma[t][i] * ((observations[t] - self.mu[i]) ** 2) for t in range(T)) / gamma_sum
                self.sigma[i] = math.sqrt(max(var_i, 1e-6))

            # Ensure State 0 is always the lower-volatility (Calm) state
            if self.sigma[0] > self.sigma[1]:
                self.mu[0], self.mu[1] = self.mu[1], self.mu[0]
                self.sigma[0], self.sigma[1] = self.sigma[1], self.sigma[0]
                self.A = [
                    [self.A[1][1], self.A[1][0]],
                    [self.A[0][1], self.A[0][0]]
                ]
                self.pi = [self.pi[1], self.pi[0]]

            # Check convergence
            diff = abs(self.mu[0] - old_mu[0]) + abs(self.mu[1] - old_mu[1])
            if diff < tol:
                print(f"Converged at iteration {iteration+1}!")
                break

    def predict_states(self, observations):
        """
        Viterbi Algorithm: Finds the single most likely path of states
        [0, 0, 0, 1, 1, 0, ...] over the entire history.
        """
        T = len(observations)
        V = [{}]
        path = {}

        # t = 0
        for s in (0, 1):
            emit = self.gaussian_pdf(observations[0], s)
            V[0][s] = math.log(max(self.pi[s], 1e-12)) + math.log(max(emit, 1e-100))
            path[s] = [s]

        # t = 1 .. T-1
        for t in range(1, T):
            V.append({})
            newpath = {}
            for curr_state in (0, 1):
                emit = self.gaussian_pdf(observations[t], curr_state)
                log_emit = math.log(max(emit, 1e-100))
                
                # Pick best previous state
                (prob, prev_state) = max(
                    (V[t-1][p] + math.log(max(self.A[p][curr_state], 1e-12)) + log_emit, p)
                    for p in (0, 1)
                )
                V[t][curr_state] = prob
                newpath[curr_state] = path[prev_state] + [curr_state]
            path = newpath

        # Find final state with highest probability
        (prob, final_state) = max((V[T-1][s], s) for s in (0, 1))
        return path[final_state]

    def get_summary(self):
        """
        Returns intuitive financial summary of the learned regimes.
        """
        # Duration formula (FRM concept): Expected days in State i = 1 / (1 - P_ii)
        calm_duration = 1.0 / (1.0 - self.A[0][0])
        panic_duration = 1.0 / (1.0 - self.A[1][1])
        
        # Annualized values (252 trading days per year)
        calm_ann_ret = self.mu[0] * 252
        calm_ann_vol = self.sigma[0] * math.sqrt(252)
        
        panic_ann_ret = self.mu[1] * 252
        panic_ann_vol = self.sigma[1] * math.sqrt(252)

        return {
            'calm': {
                'daily_ret': self.mu[0],
                'annual_ret': calm_ann_ret,
                'daily_vol': self.sigma[0],
                'annual_vol': calm_ann_vol,
                'persistence': self.A[0][0],
                'expected_duration_days': calm_duration
            },
            'panic': {
                'daily_ret': self.mu[1],
                'annual_ret': panic_ann_ret,
                'daily_vol': self.sigma[1],
                'annual_vol': panic_ann_vol,
                'persistence': self.A[1][1],
                'expected_duration_days': panic_duration
            },
            'transition_matrix': self.A
        }

if __name__ == "__main__":
    # Test on our saved Nifty dataset
    csv_path = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/nifty_vix_clean.csv"
    
    dates = []
    nifty_prices = []
    vix_prices = []
    returns = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dates.append(row['date'])
            nifty_prices.append(float(row['nifty_close']))
            vix_prices.append(float(row['vix_close']))
            returns.append(float(row['nifty_ret']))

    hmm = SimpleGaussianHMM2State()
    hmm.fit(returns)
    states = hmm.predict_states(returns)
    summary = hmm.get_summary()

    print("\n=======================================================")
    print("   NIFTY 50 2-STATE HIDDEN MARKOV MODEL RESULTS       ")
    print("=======================================================")
    
    c = summary['calm']
    p = summary['panic']
    
    print("\n1. REGIME 0: 'CALM BULL' (Normal Market Mood)")
    print(f"   - Average Daily Return:   {c['daily_ret']:+.2f}%  (Annualized: {c['annual_ret']:+.2f}%)")
    print(f"   - Daily Volatility:        {c['daily_vol']:.2f}%   (Annualized: {c['annual_vol']:.2f}%)")
    print(f"   - Stickiness (P00):        {c['persistence']*100:.1f}% chance of staying Calm tomorrow")
    print(f"   - Average Duration:        {c['expected_duration_days']:.1f} trading days (~{c['expected_duration_days']/21:.1f} months)")
    
    print("\n2. REGIME 1: 'CORRECTION / PANIC' (Turbulent Mood)")
    print(f"   - Average Daily Return:   {p['daily_ret']:+.2f}%  (Annualized: {p['annual_ret']:+.2f}%)")
    print(f"   - Daily Volatility:        {p['daily_vol']:.2f}%   (Annualized: {p['annual_vol']:.2f}%)")
    print(f"   - Stickiness (P11):        {p['persistence']*100:.1f}% chance of staying Panic tomorrow")
    print(f"   - Average Duration:        {p['expected_duration_days']:.1f} trading days (~{p['expected_duration_days']/21:.1f} months)")

    calm_days = sum(1 for s in states if s == 0)
    panic_days = sum(1 for s in states if s == 1)
    print("\n3. HISTORICAL BREAKDOWN (10 Years: 2,449 Trading Sessions):")
    print(f"   - Calm Days:  {calm_days} ({calm_days/len(states)*100:.1f}%)")
    print(f"   - Panic Days: {panic_days} ({panic_days/len(states)*100:.1f}%)")

    # Save state-labeled dataset
    output_labeled = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/nifty_regimes_labeled.csv"
    with open(output_labeled, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'nifty_close', 'vix_close', 'nifty_ret', 'regime', 'regime_name'])
        for d, n, v, r, s in zip(dates, nifty_prices, vix_prices, returns, states):
            name = "CALM" if s == 0 else "PANIC"
            writer.writerow([d, n, v, r, s, name])
            
    print(f"\nLabeled dataset saved to {output_labeled}")
