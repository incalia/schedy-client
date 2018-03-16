Frequently Asked Questions
==========================

There's something I want to ask you, how can I contact you?
-----------------------------------------------------------

Feel free to contact us using the chat integrated in our `website <https://schedy.io/>`_!

Can I use string/array/dictionaries as hyperparameters?
-------------------------------------------------------

Yes you can. However, when using the command-line, you most likely want to put
single quotes around the value, because JSON notation uses reserved Bash
caracters.

For instance:

.. code-block:: bash

   # Notice that you have to surround strings with double-quotes, because
   # that's how JSON strings work
   schedy push MyExperiment -p my_string_param '"string value"'
   schedy push MyExperiment -p my_array_param '["stuff", true, 6]'
   schedy push MyExperiment -p my_dict_param '{"key0": "value0", "key1": 42}'

I think I found a bug. How can I report it?
-------------------------------------------

First of all, we want to thank you for contributing! You can report bugs on our `GitHub tracker <https://github.com/incalia/schedy-client/issues>`_.
