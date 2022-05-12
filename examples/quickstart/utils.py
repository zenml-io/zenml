from IPython.display import HTML, display


def display_restart_button():
    display(
        HTML(
            """
            <script>
                code_show = false;
                function restart(){
                    IPython.notebook.kernel.restart();
                }
                function code_toggle() {
                    if (code_show) {
                        $('div.input').hide(200);
                    } else {
                        $('div.input').show(200);
                    }
                    code_show = !code_show
                }
            </script>
            <button onclick="restart()">Click to Restart Kernel</button>
        """
        )
    )
