# May 2023 Math AI SL Paper 1 — HTML bodies for preview only (from LaTeX export).
# Images live in static website/images/ib_paper_may2023/

PAPER_META = {
    "title": "Mathematics: applications and interpretation — Standard level · Paper 1",
    "subtitle": "8 May 2023 · Zone A afternoon | Zone B morning | Zone C afternoon",
    "time": "1 hour 30 minutes",
    "notes": "Rough preview for authoring — not the live question bank format.",
}

PAPER_QUESTIONS = [
    {
        "num": 1,
        "marks": 5,
        "image": None,
        "body": """
<p>Zaha is designing a bridge to cross a river. She believes that the weight of the steel needed for this bridge is approximately $53\\,632\\,000\\ \\mathrm{kg}$.</p>
<p>The exact weight of the steel needed for the bridge is $55\\,625\\,000\\ \\mathrm{kg}$.</p>
<p><strong>(a)</strong> Find the percentage error in Zaha's approximation.</p>
<p>Zaha's design is used to build five identical bridges.</p>
<p><strong>(b)</strong> (i) Find the weight of the steel needed for these five bridges, to three significant figures.<br/>
(ii) Write down your answer to part (b)(i) in the form $a \\times 10^{k}$, where $1 \\le a \\lt 10$, $k \\in \\mathbb{Z}$.</p>
""",
    },
    {
        "num": 2,
        "marks": 6,
        "image": None,
        "body": """
<p>Angel has $\\$520$ in his savings account. Angel considers investing the money for 5 years with a bank. The bank offers an annual interest rate of $1.2\\%$ compounded <strong>quarterly</strong>.</p>
<p><strong>(a)</strong> Calculate the amount of money Angel would have at the end of 5 years with the bank. Give your answer correct to two decimal places.</p>
<p>Instead of investing the money, Angel decides to buy a phone that costs $\\$520$. At the end of 5 years, the phone will have a value of $\\$30$. It may be assumed that the depreciation rate per year is constant.</p>
<p><strong>(b)</strong> Calculate the annual depreciation rate of the phone.</p>
""",
    },
    {
        "num": 3,
        "marks": 7,
        "image": "website/images/ib_paper_may2023/4108bb7b-f3e3-487f-89c2-57a89f48fc01-05.jpg",
        "body": """
<p>In a school, 200 students solved a problem in a mathematics competition. Their times to solve the problem were recorded and the following <strong>cumulative frequency graph</strong> was produced.</p>
<p><strong>(a)</strong> Use the graph to find</p>
<ul>
<li>(i) the median time;</li>
<li>(ii) the lower quartile;</li>
<li>(iii) the upper quartile;</li>
<li>(iv) the interquartile range.</li>
</ul>
<p>Cedric took 14 seconds to solve the problem.</p>
<p><strong>(b)</strong> Determine whether Cedric's time is an outlier.</p>
""",
    },
    {
        "num": 4,
        "marks": 6,
        "image": None,
        "body": """
<p>At a running club, Sung-Jin conducts a test to determine if there is any association between an athlete's age and their best time taken to run 100 m. Eight athletes are chosen at random:</p>
<table class="table table-sm table-bordered" style="max-width:36rem;font-size:.9rem;">
<tr><th>Athlete</th><th>A</th><th>B</th><th>C</th><th>D</th><th>E</th><th>F</th><th>G</th><th>H</th></tr>
<tr><td>Age (years)</td><td>13</td><td>17</td><td>22</td><td>18</td><td>19</td><td>25</td><td>11</td><td>36</td></tr>
<tr><td>Time (s)</td><td>13.4</td><td>14.6</td><td>13.4</td><td>12.9</td><td>12.0</td><td>11.8</td><td>17.0</td><td>13.1</td></tr>
</table>
<p>Sung-Jin decides to calculate <strong>Spearman's rank correlation coefficient</strong> for his set of data.</p>
<p><strong>(a)</strong> Complete the table of ranks (age rank / time rank for each athlete).</p>
<p><strong>(b)</strong> Calculate Spearman's $r_s$.</p>
<p><strong>(c)</strong> Interpret this value of $r_s$ in the context of the question.</p>
<p><strong>(d)</strong> Suggest a mathematical reason why Sung-Jin may have decided not to use Pearson's product-moment correlation coefficient with his data from the original table.</p>
""",
    },
    {
        "num": 5,
        "marks": 4,
        "image": None,
        "body": """
<p>The following frequency distribution table shows the test grades for a group of students.</p>
<table class="table table-sm table-bordered" style="max-width:28rem;font-size:.9rem;">
<tr><th>Grade</th><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td></tr>
<tr><th>Frequency</th><td>1</td><td>4</td><td>7</td><td>9</td><td>$p$</td><td>9</td><td>4</td></tr>
</table>
<p>For this distribution, the mean grade is $4.5$.</p>
<p><strong>(a)</strong> Write down the total number of students in terms of $p$.</p>
<p><strong>(b)</strong> Calculate the value of $p$.</p>
""",
    },
    {
        "num": 6,
        "marks": 6,
        "image": None,
        "body": """
<p>A company classifies meal quality as <em>perfect</em>, <em>satisfactory</em>, or <em>poor</em> across breakfast, lunch, and dinner (500 items inspected):</p>
<table class="table table-sm table-bordered" style="max-width:40rem;font-size:.85rem;">
<tr><th>Meal</th><th>Perfect</th><th>Satisfactory</th><th>Poor</th><th>Total</th></tr>
<tr><td>Breakfast</td><td>101</td><td>124</td><td>7</td><td>232</td></tr>
<tr><td>Lunch</td><td>68</td><td>81</td><td>5</td><td>154</td></tr>
<tr><td>Dinner</td><td>35</td><td>69</td><td>10</td><td>114</td></tr>
<tr><th>Total</th><td>204</td><td>274</td><td>22</td><td>500</td></tr>
</table>
<p>An item is chosen at random from these 500.</p>
<p><strong>(a)</strong> Find $\\mathrm{P}$ (quality is not perfect $\\mid$ breakfast).</p>
<p>A $\\chi^2$ test at the $5\\%$ significance level is carried out. Critical value $= 9.488$.</p>
<p>$\\mathrm{H}_0$: quality and meal type are independent. $\\mathrm{H}_1$: not independent.</p>
<p><strong>(b)</strong> Find the $\\chi^2$ statistic.<br/>
<strong>(c)</strong> State, with justification, the conclusion for this test.</p>
""",
    },
    {
        "num": 7,
        "marks": 6,
        "image": "website/images/ib_paper_may2023/4108bb7b-f3e3-487f-89c2-57a89f48fc01-11.jpg",
        "body": """
<p>Ani owns four cafés represented by points $\\mathrm{A},\\mathrm{B},\\mathrm{C},\\mathrm{D}$. An incomplete <strong>Voronoi diagram</strong> is given (1 unit = 1 km).</p>
<p>The midpoint of $[\\mathrm{CD}]$ is $(5.5,\\,1.5)$.</p>
<p><strong>(a)</strong> Show that the equation of the perpendicular bisector of $[\\mathrm{CD}]$ is $y = -3x + 18$.</p>
<p><strong>(b)</strong> Complete the Voronoi diagram shown above.</p>
<p>An office is equidistant from cafés $\\mathrm{B}$, $\\mathrm{C}$, and $\\mathrm{D}$. The perpendicular bisector of $[\\mathrm{BC}]$ is $3y = 2x - 1.5$.</p>
<p><strong>(c)</strong> Find the coordinates of the office.</p>
""",
    },
    {
        "num": 8,
        "marks": 5,
        "image": "website/images/ib_paper_may2023/4108bb7b-f3e3-487f-89c2-57a89f48fc01-13.jpg",
        "body": """
<p>Ruhi buys ice cream in the shape of a <strong>sphere</strong> of radius $3.4\\ \\mathrm{cm}$, served in a <strong>cone</strong>. Assume $\\frac{1}{5}$ of the ice cream volume is inside the cone (diagram not to scale).</p>
<p><strong>(a)</strong> Calculate the volume of ice cream that is <em>not</em> inside the cone.</p>
<p>The cone has slant height $11\\ \\mathrm{cm}$ and radius $3\\ \\mathrm{cm}$. The outside of the cone is covered with chocolate.</p>
<p><strong>(b)</strong> Calculate the surface area of the cone that is covered with chocolate (nearest $\\mathrm{cm}^2$).</p>
""",
    },
    {
        "num": 9,
        "marks": 6,
        "image": None,
        "body": """
<p>Lengths of seeds from a mango tree are approximated by $\\mathcal{N}(4,\\,0.25^2)$ cm.</p>
<p><strong>(a)</strong> Calculate the probability that a randomly chosen seed has length less than $3.7\\ \\mathrm{cm}$.</p>
<p>It is known that $30\\%$ of seeds have length greater than $k\\ \\mathrm{cm}$.</p>
<p><strong>(b)</strong> Find $k$.</p>
<p>For a random seed of length $d$ cm, $\\mathrm{P}(4-m \\lt d \\lt 4+m)=0.6$.</p>
<p><strong>(c)</strong> Find $m$.</p>
""",
    },
    {
        "num": 10,
        "marks": 8,
        "image": None,
        "body": """
<p>A basketball's height is modelled by</p>
$$h(t) = -4.75 t^2 + 8.75 t + 1.5,\\quad t \\ge 0$$
<p>where $h$ is height in metres and $t$ is time in seconds after release.</p>
<p><strong>(a)</strong> Find how long it takes to reach maximum height.</p>
<p><strong>(b)</strong> Assuming no one catches the ball, find when it hits the ground.</p>
<p>Another player catches the ball when its height is $1.2\\ \\mathrm{m}$.</p>
<p><strong>(c)</strong> Find $t$ when the catch happens.</p>
<p><strong>(d)</strong> Write down <strong>two limitations</strong> of using $h(t)$ to model the height of the basketball.</p>
""",
    },
    {
        "num": 11,
        "marks": 7,
        "image": "website/images/ib_paper_may2023/4108bb7b-f3e3-487f-89c2-57a89f48fc01-16.jpg",
        "body": """
<p>Consider $f(x) = 3x^2 - \\dfrac{5}{x}$, $x \\neq 0$. The graph of $f$ for $0 \\lt x \\le 5$ is shown on the axes in the diagram.</p>
<p><strong>(a)</strong> (i) Sketch the graph of $f$ for $-5 \\le x \\lt 0$ on the same axes.<br/>
(ii) Write down the $x$-coordinate of the local minimum point.</p>
<p><strong>(b)</strong> Use your GDC to find the solutions to $f(x) = 20$.</p>
<p><strong>(c)</strong> Write down the equation of the vertical asymptote.</p>
""",
    },
    {
        "num": 12,
        "marks": 5,
        "image": None,
        "body": """
<p>$X$ = number of times the target is hit in five attempts.</p>
<table class="table table-sm table-bordered" style="max-width:32rem;font-size:.9rem;">
<tr><th>$x$</th><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td></tr>
<tr><th>$\\mathrm{P}(X=x)$</th><td>0.15</td><td>0.2</td><td>$k$</td><td>0.16</td><td>$2k$</td><td>0.25</td></tr>
</table>
<p><strong>(a)</strong> Find $k$.</p>
<p>Player's gain (\\$) for each $x$ (negative = loss):</p>
<table class="table table-sm table-bordered" style="max-width:32rem;font-size:.9rem;">
<tr><th>$x$</th><td>0</td><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td></tr>
<tr><th>Gain</th><td>-4</td><td>-3</td><td>-1</td><td>0</td><td>1</td><td>4</td></tr>
</table>
<p><strong>(b)</strong> Determine whether this game is <em>fair</em>. Justify your answer.</p>
""",
    },
    {
        "num": 13,
        "marks": 9,
        "image": "website/images/ib_paper_may2023/4108bb7b-f3e3-487f-89c2-57a89f48fc01-19.jpg",
        "body": """
<p>An engineer models the cross-section of a dam by a curve and two straight lines (diagram). Distances are in metres.</p>
<p>The curve is $y = f(x)$. Sample values:</p>
<table class="table table-sm table-bordered" style="max-width:36rem;font-size:.9rem;">
<tr><th>$x$</th><td>0</td><td>0.5</td><td>1</td><td>1.5</td><td>2</td><td>2.5</td><td>3</td></tr>
<tr><th>$f(x)$</th><td>3</td><td>5.13</td><td>8</td><td>12.4</td><td>19</td><td>28.6</td><td>42</td></tr>
</table>
<p><strong>(a)</strong> Estimate the area for $0 \\le x \\le 3$ using the <strong>trapezoidal rule</strong> with three equal intervals.</p>
<p>Given $f'(x) = 3x^2 + 4$ on $0 \\lt x \\lt 3$.</p>
<p><strong>(b)</strong> Find an expression for $f(x)$ on that domain.</p>
<p><strong>(c)</strong> Hence find the actual area of the <em>entire</em> cross-section.</p>
""",
    },
]
