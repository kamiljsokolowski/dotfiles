" Make sure Your distro is not up to any unexpected and nasty things when it comes to vi compatibility switch
set nocompatible

" Enable intelligent auto-indenting for each filetype and filetype-specific plugins
filetype indent plugin on

" Enable syntax highlighting
syntax on
"set term=ansi
"set term=color_xterm

" Switch between buffers without saving and keep undo history for each one
"set hidden

" Prompt for saving a file instead of failing on quit
"set confirm

" Auto save on 'lost focus' (i.e. switching between buffers)
"set autowrite
"set autowriteall

" Better command line completion
set wildmenu

" Show partial commands in the last line of the screen
set showcmd

" Highlight searches
set hlsearch

" Use case insensitive search, except when usigng capital letters
set ignorecase
set smartcase

" Allow backspacing over autoindent, line breaks and start of insert action
set backspace=indent,eol,start

" Preserve indent lenght over new lines
set autoindent

" Stop certain movements from alwaus going to the first character of the line.
"set nostartofline

" Display the cursor position on the last line of the screen or in the status
" line of a window
"set ruler

" Always display the status line.
set rtp+=$HOME/.local/lib/python2.7/site-packages/powerline/bindings/vim/
set laststatus=2
set t_Co=256

" When something goes wrong ring a visual bell
"set visualbell
"set t_vb=

" Enable mouse usage
set mouse=a

" Set cmd windows height
set cmdheight=2

" Display line numbers
set number

" Quickly time out on keycodes, but never time out on mappings
set notimeout ttimeout ttimeoutlen=200

" Use <F11> to toggle between 'paste' and 'no paste'
"set pastetoggle=<F11>

" Change indentations settings from tabs to 4 spaces
set shiftwidth=4
set softtabstop=4
set expandtab
"set smarttab
"set tabstop=4

" Map Y to act like D and C, i.e. to yank until EOL, rather then act like the
" default yy
"map Y y$

" Map <C-L> (redraw screen) to also turn off search highlghting until the next
" search
"noremap <C-L> :nohl<CR><C-L>

" No ~ files
set nobackup
"set nobackupfiles
"set noswapfiles

" Unix-style line endings
set fileformat=unix
set fileformats=unix,dos


" Pathogen comes first
execute pathogen#infect()
" Powerline (~/.local/bin must be added to $PATH)
python from powerline.vim import setup as powerline_setup
python powerline_setup()
python del powerline_setup
" CtrlP (modify/update)
let g:ctrlp_map = '<c-p>'
let g:ctrlp_cmd = 'CtrlP'
let g:ctrlp_working_path_mode = 'ra'
" Syntastic
" (statusline settings do not work with Powerline plugin)
"set statusline+=%#warningmsg#
"set statusline+=%{SyntasticStatuslineFlag()}
"set statusline+=%*
let g:syntastic_always_populate_loc_list = 1
let g:syntastic_auto_loc_list = 1
let g:syntastic_check_on_open = 1
let g:syntastic_check_on_wq = 0
" Solarized
set background=dark
colorscheme solarized


" (for bad habit breaking) disable arrow keys
noremap <Up> <NOP>
noremap <Down> <NOP>
noremap <Left> <NOP>
noremap <Right> <NOP>

