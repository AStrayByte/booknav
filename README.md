# booknav

Hopefully to be able to convert between epubcfi and kobo locations so that I can sync read locations with an ereader app

# Packages

This project hopes to be entirely written in standard python with no extra packages required

# Tests

![Test Status](https://github.com/AStrayByte/booknav/actions/workflows/run-pytest.yml/badge.svg)

To run tests:

```sh
uv run pytest
```

### I have included 3 different books to test on:

| Book                | Details                                                                                               |
| ------------------- | ----------------------------------------------------------------------------------------------------- |
| Alice in Wonderland | [This was copied from the gutenberg project and is safe to copy and distribute.][Alice in Wonderland] |
| Frankenstein        | [This was copied from the gutenberg project and is safe to copy and distribute.][Frankenstein]        |
| Test                | [This is a fake epub i used to simulate the example shown in the offical documentation][EpubCFIDoc]   |

### Kepubs

There are 2 copies of Alice in Wonderland and Frankenstein.
A 2nd copy of each was made using Kepubify to test on Kepubs as well as epubs.

[Alice in Wonderland]: https://www.gutenberg.org/ebooks/11
[Frankenstein]: https://www.gutenberg.org/ebooks/84
[EpubCFIDoc]: https://idpf.org/epub/linking/cfi/#sec-path-examples

# Todo:

- [x] Add Todo List 📋
- [ ] Change out Exceptions for proper Exceptions like FileNotFoundError
- [ ] Make this a python package
- [ ] Make github action to auto upload pypi
- [ ] Reorganize Code to multiple files
- [ ] Make tests for individual functions rather than end to end.
