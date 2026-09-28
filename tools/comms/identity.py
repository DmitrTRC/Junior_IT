"""students/comms.yml — кто есть кто для courier: comms_id, код, telegram_id, репо GitHub. Приватно."""
from __future__ import annotations
import os
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # без 0/O, 1/I
REQUIRED_FIELDS = {"role", "student", "comms_id"}


class IdentityError(Exception):
    """comms.yml битый: не разобрался YAML или не хватает обязательных полей."""


@dataclass
class Person:
    role: str
    student: str
    comms_id: str
    code: str | None = None
    telegram_id: int | None = None
    github: str | None = None


class Identity:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.people: list[Person] = []
        if self.path.is_file():
            try:
                data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                raise IdentityError(f"{self.path}: битый YAML: {exc}") from exc
            if not isinstance(data, dict):
                raise IdentityError(f"{self.path}: ожидался словарь верхнего уровня")
            raw_people = data.get("people") or []
            if not isinstance(raw_people, list):
                raise IdentityError(f"{self.path}: people должен быть списком")
            for raw in raw_people:
                if not isinstance(raw, dict) or not REQUIRED_FIELDS <= raw.keys():
                    raise IdentityError(f"{self.path}: запись в people должна быть словарём "
                                         f"с полями {sorted(REQUIRED_FIELDS)}")
                self.people.append(Person(**{k: v for k, v in raw.items() if k in Person.__dataclass_fields__}))

    def by_student(self, student_id: str, role: str = "student") -> Person | None:
        return next((p for p in self.people if p.student == student_id and p.role == role), None)

    def by_comms_id(self, comms_id: str) -> Person | None:
        return next((p for p in self.people if p.comms_id == comms_id), None)

    def ensure(self, student_id: str, role: str = "student") -> Person:
        person = self.by_student(student_id, role)
        if person is None:
            prefix = "s-" if role == "student" else "p-"
            taken = {p.comms_id for p in self.people}
            comms_id = prefix + secrets.token_hex(2)
            while comms_id in taken:
                comms_id = prefix + secrets.token_hex(2)
            person = Person(role=role, student=student_id, comms_id=comms_id)
            self.people.append(person)
            self.save()
        return person

    def new_code(self, person: Person) -> str:
        # коды не проверяются на уникальность: 32^5 ≈ 33 млн вариантов,
        # коллизия на группе из трёх человек практически исключена
        chars = [secrets.choice(ALPHABET) for _ in range(5)]
        person.code = "".join(chars[:3]) + "-" + "".join(chars[3:])
        self.save()
        return person.code

    def bind(self, comms_id: str, telegram_id: int) -> Person | None:
        person = self.by_comms_id(comms_id)
        if person is None:
            return None
        person.telegram_id, person.code = int(telegram_id), None
        self.save()
        return person

    def set_github(self, student_id: str, repo: str) -> None:
        self.ensure(student_id).github = repo
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".yml.tmp")
        tmp.write_text(yaml.safe_dump({"people": [asdict(p) for p in self.people]},
                                      allow_unicode=True, sort_keys=False), encoding="utf-8")
        os.replace(tmp, self.path)
