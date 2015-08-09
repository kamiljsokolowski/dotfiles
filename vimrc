"" syntax highlight
""set term=ansi
""set term=color_xterm
syntax on

"" numbering
""set number

"" no ~ files
set nobackup
""set nobackupfiles
""set noswapfiles

"" set tab width
set tabstop=4		"" hard tabstop
set shiftwidth=4		"" size of an indent
set softtabstop=4		"" combination of spaces and tabs used to simulate tab stops other then the hard one
""set smarttab
""set expandtab

"" associate *.scr with tcl filetype
""au BufRead,BufNewFile *.scr setfiletype tcl
au BufRead,BufNewFile *.scr set filetype=tcl
