#use
	
	use File::stat qw(stat);
	
sub LoadFileAsString {
	local ( $file ) = @_;
	local ( $keyfile ) ;
	open( FILE, $file );
	while(<FILE>) {
		s/^ *\n//;
		tr/\t/ /;
		$keyfile = "$keyfile$_";
		}
	
	close ( FILE );
	$keyfile; }
# main
	$cmd_line = $ENV{'QUERY_STRING'} ;
	print( "ARG = $cmd_line  \n" );
	($cmd_line) = @ARGV;
	print( "ARG = $cmd_line  \n" );
	$outputVFC =  "$cmd_line.vfc" ;
	$file = $cmd_line ;
	print( STDOUT  "listening and autoparse for file =  $cmd_line  ...  \n" );
	$lasttime = 0;
	$I = 2;
	Parse();
	while( $I < 1 ) {
		$I = $I+1;
		$nowtime = stat($file)->mtime;
		
		
		if ( $nowtime != $lasttime )
		{
			Parse();
			$lasttime = stat($file)->mtime;
			print( STDOUT  "\nlistening and autoparse for file =  $cmd_line  ...  \n" );
		}else{
			}
		
		select(undef, undef, undef, 0.25);
		}
	
	print "done\n";
	
sub Parse{
	open OUTFILE,  ">" ,   $outputVFC  or die "Cannot open output: $!";
	open( FILE, $cmd_line );
	my @stack;
	$lastcount = 0;
	$indent = 1;
	$ParsedFile  = "";
	while(<FILE>) {
		$_ =~ s/    /\t/ ;
		$_ =~ s/\n// ;
		$T =$_;
		$T =~ s/\t+$//g;
		$count = s/\t//g + 1;
		
		$change = $lastcount - $count ;
		$comment = "$_";
		while ( $lastcount - $count > 0 ) {
			$stack_value = pop( @stack );
			if ( $stack_value =~ m/bendend/  )
			{
				$line ="bend();";
				$ParsedFile  = "$ParsedFile$line\n";
				$line = "end();";
				$ParsedFile  = "$ParsedFile$line\n";
			}else{
				if (  $stack_value =~ m/lend/ )
				{
					$line ="$stack_value();";
					$ParsedFile  = "$ParsedFile$line\n";
					$line ="set();";
					$ParsedFile  = "$ParsedFile$line\n";
				}else{
					if ( $stack_value =~ m/pend/ )
					{
						
						$line ="bend();\//$comment";
						$ParsedFile  = "$ParsedFile$line\n";
					}else{
						if ( $stack_value =~ m/bend/ )
						{
							if ( m/$PEND/  || m/$PATH/  )
							{
								
								
							}else{
								
								$line ="$stack_value();\//$comment";
								$ParsedFile  = "$ParsedFile$line\n";
								}
						}else{
							if ( $stack_value =~ m/wend/ )
							{
								$line ="bend();\//$comment";
								$ParsedFile  = "$ParsedFile$line\n";
							}else{
								if ( $stack_value =~ m/end/ )
								{
									$line ="$stack_value();\//$comment";
									$ParsedFile  = "$ParsedFile$line\n";
									}
								}
							}
						}
					}
				}
			$lastcount = $lastcount - $indent;
			}
		
		$lastcount = $count;
		s/^\s*//;
		
		
		s/#.*$//;
		if ( $comment =~ s/^.*#{1}//  )
		{
			if ( $comment =~ m/^end/ )
			{
				$line ="end($_);\//$comment";
			}else{
				$line ="set($_);\//$comment";
				}
		} else {
			$comment = "";
			}
		
		$line ="set($_);\//$comment";
		
		$LOOP = "^\s*(for|while)\s*.*:";
		$BRANCH = "^\s*(if|try)\s*.*:";
		$WITH = "^\s*(with)\s*.*:";
		$PATH = "^\s*(elif)\s*.*:";
		$PEND = "^\s*(else|except)\s*.*:";
		$END = "^\s*(break|continue|return).*";
		$OUTPUT = "^\s*(print).*";
		$INPUTOBJ = "^\s*(class).*:";
		$INPUT = "^\s*(def).*:";
		$EVENT = "^\s*(import).*";
		
				if(   m/$INPUTOBJ/  )  {
			$line ="input($_);\//$comment";
			$ParsedFile  = "$ParsedFile$line\n";
			$line ="branch();";
			push( @stack, "bendend" );
		} if(   m/$INPUT/  )  {
			$line ="input($_);\//$comment";
			push( @stack, "end" );
		} if(   m/$EVENT/  )  {
			$line ="event($_);\//$comment";
		} if(   m/$OUTPUT/  )  {
			$line ="output($_);\//$comment";
		} if(   m/$LOOP/  )  {
			$line ="loop($_);\//$comment";
			push( @stack, "lend" );
		} if(   m/$WITH/  )  {
			$line ="branch($_);\//$comment";
			$ParsedFile  = "$ParsedFile$line\n";
			$line ="path();";
			push( @stack, "wend" );
		} if(   m/$BRANCH/  )  {
			$line ="branch($_);\//$comment";
			$ParsedFile  = "$ParsedFile$line\n";
			$line ="path();";
			push( @stack, "bend" );
		} if(   m/$PATH/  )  {
			$line ="path($_);\//$comment";
			push( @stack, "path" );
		} if(   m/$PEND/  )  {
			$stack_value = pop( @stack );
			if ( $stack_value =~ "bend" )
			{
				
				
			}else{
				push( @stack, $stack_value );
				}
			$line ="path($_);\//$comment";
			push( @stack, "pend" );
		} if(   m/$END/  )  {
			$line ="end($_);\//$comment";
			}
		$ParsedFile  = "$ParsedFile$line\n";
		$line = "";
		}
	
	close ( FILE );
	
	$stack_value = pop( @stack );
	while( $stack_value  ) {
		$line ="$stack_value();";
		$ParsedFile  = "$ParsedFile$line\n";
		$stack_value = pop( @stack );
		}
	
	print( OUTFILE $ParsedFile );
	printFooter( );
	close ( OUTFILE );
	print(  "E:\\VFC1.0\\vfc2000 $outputVFC -Reload" );
	system(  "E:\\VFC1.0\\vfc2000 $outputVFC -Reload" );
	
	}
sub printFooter{
	$rootfile = $file;
	$rootfile =~ s/^.*\\//;
	print( OUTFILE  ";INSECT" );
	print( OUTFILE  "A EMBEDDED SESSION INFORMATION\n" );
	print( OUTFILE  "; 255 16777215 65280 16777088 16711680 255 8388608 0 255 255 65535 65280 4210688 \n");
	print( OUTFILE  "$rootfile.py   #\"\"\"  #\"\"\"  \n");
	print( OUTFILE  "; notepad++.exe \n");
	print( OUTFILE  ";INSECT" );
	print( OUTFILE  "A EMBEDDED ALTSESSION INFORMATION\n");
	print( OUTFILE  "; 262 123 765 1694 0 170   379   4294966903    python.key  0");
	}
#  Export  Date: 01:44:48 PM - 29:Jun:2021.

