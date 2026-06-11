## Mail Cleanup Helper for TStaff

Currently, to clean up junk mail on onion using Postfix (https://www.postfix.org/postsuper.1.html), one has to either call `postsuper -d [queue id]` on every piece of junk mail or call the sweeping `postsuper -d all` to delete all mail in the queue. More specific grouping (by email address, for example), while somewhat-supported by Postfix, is difficult in our case because spam mail addresses are frequently different in our logs. This script aims to make the process of clearing junk mail less arduous while maintaining the same level of scrutinty as deliberate manual removal.

In short, this script searches for keywords in sender emails (e.g, "Kroger" or "Verizon") and then returns a list of `postsuper -d` commands with matched IDs. By default, users have to approve/confirm matched emails are junk before their IDs are considered spam to avoid deleting important email that's stuck on the queue. 

To run the program, follow these steps:

1. clone this repo onto your local machine (or wherever Python can run). This DOES NOT (and probably should not) run on onion.
2. On onion, run `clear` and then `mailq`. Copy the output of `mailq` and paste it into `queue.txt`, which will always be empty on the remote repository to preserve privacy.
3. Decide whether you want to remove a single key/spam type -- say, just Verizon -- , or multiple -- say, Kroger, Verizon, and more. For the single term case, you can simply run `python clean_mailq.py [term]`. For multiple terms, you must type every spam word you wish to check for in `spam_words.txt` separated by newlines, like so:

        walmart
        lowes
        kroger
        cvs
        marriot
        sams
        verizon
        
    Then, you can run `python clean_mailq.py all`, which will check for all of the spam terms you listed in the `spam_words.txt` file. This file is also empty on the remote repository to preserve privacy.

4. The output of these commands will be a list that looks like this:

        postsuper -d ID1
        postsuper -d ID2
        postsuper -d ID3
        postsuper -d ID4

    On onion, copy and paste these, as root, to delete the junk mail. You should see the changes reflected by running a `grep` on a specific ID or `mailq` to see the total count of email decrease.

If you want to see a video demo of how to use this, please click this link and request access: https://drive.google.com/file/d/1T9C97OzdA52oNaVM5kAdTpMntDXK2Ueu/view?usp=sharing



Notes: 
- Planned updates: I intended to allow upper limits on how many postsuper commands can be printed by the command before exiting. This will help users who only want to/have time to remove 50, 100, etc emails at a time
- I made this using Copilot (since it's largely parsing and pattern matching anyways) in 45 mins after an hour-ish of planning it out. The code does not actually delete anything and requires user confirmation to even suggest deletion commands, making largely safe/harmless. Put differently, it is still entirely on the user to copy and paste `postsuper -d` commands that actually delete emails.