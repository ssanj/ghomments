import sublime
import sublime_plugin
import os
import logging
import json
import html


class GhommentsPreloaderCommand(sublime_plugin.EventListener):

    DEFAULT_PURS_HOME= os.path.expanduser("~/.purs")

    def is_purs_checkout(self, file_name):
        # Override this from config
        common = os.path.commonprefix([self.DEFAULT_PURS_HOME, file_name])
        return common == self.DEFAULT_PURS_HOME

    def get_window_ghomment_config(self, window):
        return window.settings().get("ghomment")

    def set_window_ghomment_config(self, window):
        window.settings().set("ghomment", True)
        print("set and get: {}".format(window.settings().get("ghomment")))


    def unset_window_ghomment_config(self, window):
        window.settings().set("ghomment", False)

    def on_load_async(self, view):
        window = view.window()
        if self.get_window_ghomment_config(window) is None: #config not set
            if self.is_purs_checkout(view.file_name()): # valid config
                self.set_window_ghomment_config(window)
                print("Ghomments: active")
            else:
                self.unset_window_ghomment_config(window)
                print("Ghomments: inactive")

        if self.get_window_ghomment_config(window):
            print("Ghomments: loading comments")
            if self.has_comments(view):
                view.run_command('ghomments')
        else:
            print("Ghomments: not loading comments")

    def has_comments(self, view):
        if view.file_name():
            full_file_name = view.file_name()
            file_dir = os.path.dirname(full_file_name)
            file_name = os.path.basename(full_file_name)
            comment_file_name = "{}.comment".format(file_name)

            comment_file = os.sep.join([file_dir, comment_file_name])
            print("Ghomments: file_dir: {}".format(file_dir))
            print("Ghomments: file_name: {}".format(file_name))
            print("Ghomments: comment_file_name: {}".format(comment_file_name))
            print("Ghomments: final comment file: {}".format(comment_file))
            has_comments = os.path.exists(comment_file)
            print("Ghomments: has comment file: {}".format(has_comments))
            return has_comments


class GhommentsCommand(sublime_plugin.TextCommand):

    comment_regions = []
    comment_index = None

    def is_enabled(self):
        if self.view and self.view.file_name():
            return True
        else:
            return False

    def is_visible(self):
        return self.is_enabled()

    def run(self, edit, **args):
        FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(format=FORMAT)
        self.logger = logging.getLogger('ghomments.plugin')
        self.logger.debug("regions: {}".format(str(self.comment_regions)))

        # remove any existing phantoms
        if args.get('reset'):
            print("resetting all the things")
            self.reset()
            return

        if args.get('index') and len(self.comment_regions) != 0:
            self.logger.debug("has index supplied")
            if self.comment_index is not None: #already used
                self.comment_index = (self.comment_index + 1) % len(self.comment_regions)
                self.logger.debug("index is {}".format(self.comment_index))
            else: #first use
                self.logger.debug("index is 0")
                self.comment_index = 0

            if not hasattr(self, "phantoms"):
                self.logger.debug("no phantoms, rerendering")
                self.perform()

            self.view.show_at_center(self.comment_regions[self.comment_index])
        else:
            self.logger.debug("rendering element")
            self.perform()

    # def is_visible(self):
    #     return scoggle.Scoggle.is_visible(self.view, sublime.version())

    def reset(self):
        self.comment_index = 0
        self.comment_regions = []

        self.ps = sublime.PhantomSet(self.view, "GHComments")
        self.phantoms = []
        self.ps.update(self.phantoms)

    def perform(self):
        self.logger.setLevel(logging.DEBUG);
        file_name = self.view.file_name()

        if file_name:
            comment_file_name = "{}.{}".format(file_name, "comment")
            if os.path.exists(comment_file_name):
                self.logger.debug("file found")
                with open(comment_file_name, encoding='utf-8') as comment_file:
                    data = json.load(comment_file)
                    line_markup_dict = self.get_file_comments(data)
                    self.show_phantoms(line_markup_dict)

            else:
                self.logger.debug("comment file not found")
        else:
            self.logger.debug("no file name")

    def show_phantoms(self, line_markup_dict):
        # self.logger.debug("spooky")
        self.view.erase_phantoms("GHComments") # remove all existing phantoms
        self.ps = sublime.PhantomSet(self.view, "GHComments")
        self.phantoms = []

        comment_lines = self.get_header_lines(line_markup_dict.keys())

        header_markup = '''
            <body id="gh-comment-heading">
                <style>
                        .gh-comment-heading {{
                          background-color:  white;
                          color: color(var(--bluish));
                          font-weight: bold;
                          margin: 20px;
                        }}
                </style>
                <H1 class="gh-comment-heading">{}</H1>
                {}
            </body>
        '''.format("Comments added to lines:", comment_lines)

        header_line  = 0

        for (line, markup) in line_markup_dict.items():
            # TODO: Sanity check the line numbers
            r = self.view.line(sublime.Region(self.view.text_point(line, 0), self.view.text_point(line, 0)))
            self.phantoms.append(sublime.Phantom(r, markup, sublime.LAYOUT_BELOW));

            if r not in self.comment_regions:
                self.comment_regions.append(r)

        # Add the header if there are any comments to display
        if len(line_markup_dict) > 0:
            r = sublime.Region(self.view.text_point(header_line, 0), self.view.text_point(header_line, 0))
            self.phantoms.append(sublime.Phantom(r, header_markup, sublime.LAYOUT_BLOCK));

        self.ps.update(self.phantoms)

    def get_header_lines(self, lines):
        lines_format = list(map(self.get_header_line, lines))
        return "<ul>{}</ul>".format("".join(lines_format))

    def get_header_line(self, line):
       return "<li>{}</li>".format(line)

    def get_file_comments(self, data):
        file_comments = data["file_comments"]
        line_markups = list(map(self.get_line_comments, file_comments)) #List[(LineNumber, String)]
        comments_dict = dict(line_markups)
        return comments_dict

    def get_line_comments(self, lcomment):
        line_comments = lcomment['file_line_comments']
        line = lcomment['line']
        comment_result = list(map(self.get_comments, line_comments))
        all_comments_for_line = '<div class="gh-comment-separator"></div>'.join(comment_result)
        markup_for_line = '''
            <body id="gh-comment">
                <style>
                        body {{
                          background-color:  color(var(--background));
                          color: white;
                          margin: 10px;
                        }}

                        .gh-comment-line {{
                          margin-top: 10px;
                          padding: 10px;
                          border-top: 2px solid white;
                          border-bottom: 2px solid white;
                        }}

                        .gh-comment-separator {{
                          border-bottom: 1px solid var(--greenish);
                          padding-bottom: 20px;
                          margin-bottom: 20px
                        }}

                        .gh-comment-comment_link {{
                          padding-top: 10px;
                        }}

                        .gh-comment-text {{
                          word-wrap: break-word;
                          width: 1000px;
                          height: auto;
                        }}

                        .gh-comment-author {{
                          padding-bottom: 10px;
                          color: var(--orangish);
                        }}

                        code {{
                          font-style: italic;
                          font-weight: bold;
                          background-color:  color(var(--cyanish) alpha(0.75));
                          color:  var(--foreground);
                          padding-left: 2px;
                          padding-right: 2px;
                        }}
                </style>
                <div class="gh-comment-line">{}</div>
            </body>
            '''.format(all_comments_for_line)

        return (line, markup_for_line)

    def get_comments(self, comment):
        link = comment['link']
        gravatar = comment['user_icon']
        username = comment['user_name']
        sample_comment_text = comment.get('body_md')
        comment_text = sample_comment_text if sample_comment_text else comment['body']
        return '''
                <div class="gh-comment-author">
                  <img width="16" height="16" src="{}" />
                  <b>{}</b>
                </div>
                <div class="gh-comment-text">
                  {}
                </div>
                <div class="gh-comment-comment_link">
                  <a href="{}">open comment on GH</a>
                </div>
        '''.format(gravatar, username, comment_text, link)
