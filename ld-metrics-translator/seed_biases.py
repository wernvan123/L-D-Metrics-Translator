from app import create_app
from app.models import KnowledgeCategory, KnowledgeResource, db

BIAS_DATA = [
    {
        "heading": "Authority Bias",
        "tier": "t1",
        "tags": "bias,authority",
        "content": "Teams overweight directives from senior leaders, assuming rank equals correctness.",
    },
    {
        "heading": "Status Quo Bias",
        "tier": "t1",
        "tags": "bias,status quo",
        "content": "Preference for existing practices even when evidence suggests change would improve outcomes.",
    },
    {
        "heading": "Bandwagon Effect",
        "tier": "t1",
        "tags": "bias,bandwagon",
        "content": "Adopting beliefs or initiatives because many others support them, reducing critical evaluation.",
    },
    {
        "heading": "Confirmation Bias",
        "tier": "t1",
        "tags": "bias,confirmation",
        "content": "Seeking information that confirms existing beliefs while ignoring disconfirming evidence during decision reviews.",
    },
    {
        "heading": "Anchoring Bias",
        "tier": "t1",
        "tags": "bias,anchoring",
        "content": "Early numbers in forecasts anchor expectations, limiting openness to updated data from pilots or experiments.",
    },
    {
        "heading": "Availability Heuristic",
        "tier": "t1",
        "tags": "bias,availability",
        "content": "Recent or vivid incidents dominate risk perception, crowding out broader datasets when prioritizing interventions.",
    },
    {
        "heading": "Overconfidence Bias",
        "tier": "t1",
        "tags": "bias,overconfidence",
        "content": "Teams overestimate accuracy of their forecasts or readiness, skipping validation and contingency planning.",
    },
    {
        "heading": "Sunk Cost Fallacy",
        "tier": "t1",
        "tags": "bias,sunk cost",
        "content": "Past investments drive continued commitment to underperforming initiatives instead of pivoting to better options.",
    },
    {
        "heading": "Halo Effect",
        "tier": "t1",
        "tags": "bias,halo effect",
        "content": "Positive impressions of a high-status individual spill over into unwarranted confidence in all of their proposals.",
    },
    {
        "heading": "Loss Aversion",
        "tier": "t1",
        "tags": "bias,loss aversion",
        "content": "Fear of potential losses outweighs comparable gains, slowing experimentation with new learning approaches.",
    },
    {
        "heading": "Framing Effect",
        "tier": "t1",
        "tags": "bias,framing",
        "content": "Identical data leads to different choices depending on whether outcomes are framed as gains or losses.",
    },
    {
        "heading": "Fundamental Attribution Error",
        "tier": "t1",
        "tags": "bias,attribution",
        "content": "Leaders blame individual motivation for performance gaps while overlooking structural or contextual barriers.",
    },
    {
        "heading": "Survivorship Bias",
        "tier": "t2",
        "tags": "bias,survivorship",
        "content": "Successful case studies get spotlighted while lessons from failed pilots remain invisible, skewing learning pathways.",
    },
    {
        "heading": "Recency Bias",
        "tier": "t2",
        "tags": "bias,recency",
        "content": "Most recent feedback dominates memory, sidelining longer-term trends when evaluating learner progress.",
    },
    {
        "heading": "Planning Fallacy",
        "tier": "t2",
        "tags": "bias,planning",
        "content": "Teams underestimate time and resources required to embed new practices, leading to rushed or incomplete rollouts.",
    },
    {
        "heading": "Groupthink",
        "tier": "t2",
        "tags": "bias,groupthink",
        "content": "Desire for harmony suppresses dissenting views, reducing the quality of design critiques and debriefs.",
    },
    {
        "heading": "Self-Serving Bias",
        "tier": "t2",
        "tags": "bias,self-serving",
        "content": "Individuals credit successes to their own skill and attribute failures to external circumstances, limiting accountability.",
    },
    {
        "heading": "In-Group Bias",
        "tier": "t2",
        "tags": "bias,in-group",
        "content": "Preference for familiar teams or functions leads to uneven access to opportunities and resources.",
    },
    {
        "heading": "Status Bias",
        "tier": "t2",
        "tags": "bias,status",
        "content": "Statements from high-ranking voices are weighted more heavily than contributions from peers or frontline experts.",
    },
    {
        "heading": "Reactive Devaluation",
        "tier": "t2",
        "tags": "bias,devaluation",
        "content": "Ideas proposed by perceived rivals or other departments are discounted regardless of their merit.",
    },
    {
        "heading": "Escalation of Commitment",
        "tier": "t2",
        "tags": "bias,escalation",
        "content": "Leaders double down on failing strategies to justify earlier choices, even when evidence signals pivoting is wiser.",
    },
    {
        "heading": "Optimism Bias",
        "tier": "t2",
        "tags": "bias,optimism",
        "content": "Teams underestimate risks and overestimate positive outcomes, delaying mitigation plans for foreseeable obstacles.",
    },
    {
        "heading": "Outcome Bias",
        "tier": "t2",
        "tags": "bias,outcome",
        "content": "Decisions are judged solely by results rather than the quality of the process or evidence used at the time.",
    },
    {
        "heading": "Premature Closure",
        "tier": "t2",
        "tags": "bias,diagnostic",
        "content": "Teams stop investigating root causes after finding an initial explanation, missing deeper systemic drivers.",
    },
    {
        "heading": "Conformity Bias",
        "tier": "t2",
        "tags": "bias,conformity",
        "content": "Individuals adjust their views to align with group averages, suppressing critical thinking during retrospectives.",
    },
    {
        "heading": "Time Pressure Bias",
        "tier": "t2",
        "tags": "bias,time pressure",
        "content": "Compressed timelines push people toward fast, habitual responses rather than deliberate analysis of alternatives.",
    },
    {
        "heading": "Availability Cascade",
        "tier": "t3",
        "tags": "bias,availability",
        "content": "Repeated stories gain credibility through repetition alone, driving policy shifts without rigorous validation.",
    },
    {
        "heading": "Moral Licensing",
        "tier": "t3",
        "tags": "bias,moral",
        "content": "After doing something perceived as positive, individuals feel licensed to compromise on later ethical or inclusion choices.",
    },
    {
        "heading": "Illusory Correlation",
        "tier": "t3",
        "tags": "bias,correlation",
        "content": "People see relationships between unrelated variables, leading to misguided conclusions about talent indicators.",
    },
    {
        "heading": "Expectation Bias",
        "tier": "t3",
        "tags": "bias,expectation",
        "content": "Preconceived expectations influence observation, skewing qualitative assessments or interview debriefs.",
    },
    {
        "heading": "Negativity Bias",
        "tier": "t3",
        "tags": "bias,negativity",
        "content": "Negative events receive disproportionate attention, dampening recognition of incremental progress.",
    },
    {
        "heading": "Ambiguity Effect",
        "tier": "t3",
        "tags": "bias,ambiguity",
        "content": "People avoid options with unknown probabilities, limiting experimentation with emerging learning technologies.",
    },
    {
        "heading": "Projection Bias",
        "tier": "t3",
        "tags": "bias,projection",
        "content": "Decision-makers assume others share their preferences or motivations, distorting empathy for learner needs.",
    },
]

def seed_bias_resources():
    app = create_app()
    with app.app_context():
        category = KnowledgeCategory.query.filter_by(name="Biases & Heuristics").first()
        if not category:
            category = KnowledgeCategory(name="Biases & Heuristics")
            db.session.add(category)
            db.session.commit()
        created = 0
        for item in BIAS_DATA:
            existing = KnowledgeResource.query.filter_by(heading=item["heading"], category_id=category.id).first()
            if existing:
                continue
            resource = KnowledgeResource(
                heading=item["heading"],
                content=item["content"],
                tier=item["tier"],
                tags=item["tags"],
                category=category,
            )
            db.session.add(resource)
            created += 1
        if created:
            db.session.commit()
        print(f"Seeded {created} bias resources")

if __name__ == "__main__":
    seed_bias_resources()
