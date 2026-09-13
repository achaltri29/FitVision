from services.config.workout_config import PROMPT


class LLMCoach:
    def __init__(self, groq_client):
        self.client = groq_client
        self.history = []
        self.system_prompt = PROMPT

    def reset_history(self):
        self.history = []

    def give_feedback(self, event, exercise="Exercise", issue=None):
        exercise_str = exercise if exercise else "Exercise"
        prompt = f"Exercise: {exercise_str} | Event: {event} | Form Issue: {issue if issue else 'None'}"

        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.history[-10:],
            {"role": "user", "content": prompt}
        ]

        import os
        model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.4,
        )

        text = response.choices[0].message.content.strip()

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        unique_lines = []
        for l in lines:
            if not unique_lines or l.lower() != unique_lines[-1].lower():
                unique_lines.append(l)
        cleaned_text = " ".join(unique_lines)

        self.history.append({"role": "user", "content": prompt})
        self.history.append({"role": "assistant", "content": cleaned_text})

        return cleaned_text
    