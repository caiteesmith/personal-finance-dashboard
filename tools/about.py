# tools/about.py
import streamlit as st


def render_about():
    left, center, right = st.columns([0.12, 0.76, 0.12])
    with center:
        st.title("About this Dashboard")

        with st.container(border=True):
            st.subheader("Why I built this")

            st.markdown(
                """
                In early 2025, I built a simple Excel spreadsheet because I was tired of feeling vague about my money.
                I wanted one clear place to see:

                - What I earned  
                - What I spent  
                - What I owed
                - Where I could cut expenses
                - And what was actually left  

                Using that spreadsheet, I paid off about $20,000 of debt by mid-2025, including 3 credit cards, a consolidation loan, an auto loan, a student loan, and my financed iPhone.

                That clarity helped me finally qualify for a solid mortgage and buy my home in August 2025.

                This dashboard is that spreadsheet, rebuilt as a cleaner, friendlier tool so you don't have to DIY it from scratch.
                """
            )

        with st.container(border=True):
            st.subheader("What this tool helps you understand")

            st.markdown(
                """
                **Your full monthly picture**  
                See all your income, fixed bills, essentials, non-essentials, saving, investing, and consumer debt in one place.

                **Your real breathing room**  
                Clear calculations for what's safe to spend, per month, week, and day, after your actual obligations.

                **Your debt trajectory**  
                Honest payoff timelines, estimated interest, and alerts if any payment doesn't even cover interest.

                **Your emergency minimum**  
                A grounded number showing what you truly need each month if your income stopped.

                **Your mortgage payoff path**  
                The built-in Mortgage Payoff Calculator breaks down your amortization, total interest, and how extra payments change your payoff date, whether it's monthly extras, annual contributions, or a one-time lump sum.

                Together, these give you the same clarity that helped me pay down debt, feel in control, and eventually buy a home.
                """
            )

        st.subheader("Who this is for")

        with st.container(border=True):
            st.markdown(
                """
                This is for you if you've ever thought:

                - “I make okay money... so why does it never feel like enough?”  
                - “I'm paying my cards, but I don't know when this will realistically end.”  
                - “I just want to know if I'm okay (or not) without being judged.”  
                - “Will I ever actually get out of debt?”  
                - “I wish understanding my mortgage wasn't so confusing.”

                It's not a bank-connected app, not a strict budget, and not about perfection. It's about clarity, confidence, and knowing the real numbers behind your choices.
                """
            )

        st.caption("💜 Built by someone who has lived through these same money stresses and wants to make the path feel a little easier for anyone navigating them now. 💜")

def main():
    render_about()