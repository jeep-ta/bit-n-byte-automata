import unittest
from .midterm_scenarios import run_midterm_cases


class ProjectTests(unittest.TestCase):
    def test_requirement_scenarios(self):
        for row in run_midterm_cases():
            with self.subTest(id=row['id'], scenario=row['scenario']):
                self.assertEqual(row['expected'], row['actual'])


if __name__ == '__main__':
    unittest.main()
